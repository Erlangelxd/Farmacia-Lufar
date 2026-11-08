"""Servicios transaccionales de inventario.

Toda alteración de existencias pasa por este módulo. El servicio actualiza el
stock del lote y registra un movimiento inmutable dentro de la misma
transacción, de modo que el historial siempre pueda reconstruirse.
"""

from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F, Q, Sum
from django.utils import timezone

from .models import (
    AjusteCostoInventario,
    AsignacionCostoInventario,
    CapaCosto,
    Lote,
    MovimientoInventario,
)

STOCK_MAXIMO = Decimal("9999999999.99")
CANTIDAD_MINIMA = Decimal("0.01")
TIPOS_MANUALES = (
    MovimientoInventario.Tipo.ENTRADA,
    MovimientoInventario.Tipo.SALIDA,
    MovimientoInventario.Tipo.AJUSTE_POSITIVO,
    MovimientoInventario.Tipo.AJUSTE_NEGATIVO,
)


def _decimal(valor, mensaje: str) -> Decimal:
    """Convierte un valor a ``Decimal`` y devuelve un error legible."""
    try:
        return Decimal(str(valor))
    except (InvalidOperation, TypeError, ValueError):
        raise ValidationError(mensaje) from None


def _validar_cantidad(cantidad) -> Decimal:
    """Valida que la cantidad sea positiva, con dos decimales y acotada."""
    cantidad = _decimal(cantidad, "La cantidad no es válida.")

    if cantidad < CANTIDAD_MINIMA:
        raise ValidationError("La cantidad debe ser mayor que cero.")
    if cantidad > STOCK_MAXIMO:
        raise ValidationError("La cantidad excede el máximo permitido.")
    if cantidad != cantidad.quantize(Decimal("0.01")):
        raise ValidationError(
            "La cantidad admite como máximo dos decimales."
        )
    return cantidad


def _validar_costo(costo_unitario):
    if costo_unitario in (None, ""):
        return None
    costo = _decimal(costo_unitario, "El costo unitario no es válido.")
    if costo < 0 or costo > Decimal("99999999.99"):
        raise ValidationError("El costo unitario está fuera de rango.")
    if costo != costo.quantize(Decimal("0.01")):
        raise ValidationError("El costo unitario admite dos decimales.")
    return costo


def _validar_usuario(usuario) -> None:
    if usuario is None or not getattr(usuario, "is_authenticated", False):
        raise ValidationError(
            "Se requiere un usuario autenticado para registrar el movimiento."
        )


def _aplicar_movimiento(
    lote: Lote,
    *,
    tipo: str,
    cantidad: Decimal,
    usuario,
    motivo: str = "",
    detalle_venta=None,
    costo_unitario=None,
    asignaciones_costo=None,
) -> MovimientoInventario:
    """Aplica el movimiento sobre un lote ya bloqueado dentro de la transacción."""
    _validar_usuario(usuario)
    motivo = " ".join((motivo or "").split())

    signo = 1 if tipo in MovimientoInventario.TIPOS_ENTRADA else -1
    nuevo_stock = lote.stock_actual + (cantidad * signo)

    if nuevo_stock < Decimal("0.00"):
        raise ValidationError(
            f"El lote {lote.codigo_lote} no tiene existencias suficientes: "
            f"stock actual {lote.stock_actual}."
        )
    if nuevo_stock > STOCK_MAXIMO:
        raise ValidationError(
            "El stock resultante excede el máximo permitido."
        )

    costo_total = None
    costo_unitario = _validar_costo(costo_unitario)
    if tipo in MovimientoInventario.TIPOS_ENTRADA:
        if costo_unitario is not None:
            costo_total = (cantidad * costo_unitario).quantize(
                Decimal("0.01")
            )
    else:
        asignaciones_costo = asignaciones_costo or _preparar_asignaciones(
            lote, cantidad
        )
        if all(item["costo_unitario"] is not None for item in asignaciones_costo):
            costo_total = sum(
                (
                    item["cantidad"] * item["costo_unitario"]
                    for item in asignaciones_costo
                ),
                Decimal("0.00"),
            ).quantize(Decimal("0.01"))

    lote.stock_actual = nuevo_stock
    lote.save(update_fields=["stock_actual", "actualizado_en"])

    movimiento = MovimientoInventario.objects.create(
        lote=lote,
        tipo=tipo,
        cantidad=cantidad,
        stock_resultante=nuevo_stock,
        costo_total=costo_total,
        detalle_venta=detalle_venta,
        motivo=motivo,
        usuario=usuario,
    )
    if tipo in MovimientoInventario.TIPOS_ENTRADA:
        CapaCosto.objects.create(
            lote=lote,
            movimiento_entrada=movimiento,
            cantidad_inicial=cantidad,
            cantidad_restante=cantidad,
            costo_unitario=costo_unitario,
        )
    else:
        for asignacion in asignaciones_costo:
            capa = asignacion["capa"]
            capa.cantidad_restante -= asignacion["cantidad"]
            capa.save(update_fields=["cantidad_restante"])
            AsignacionCostoInventario.objects.create(
                movimiento=movimiento,
                capa=capa,
                cantidad=asignacion["cantidad"],
                costo_unitario=asignacion["costo_unitario"],
            )
    return movimiento


def _preparar_asignaciones(lote: Lote, cantidad: Decimal) -> list[dict]:
    """Reserva capas FIFO dentro del lote y concilia saldos sin costo heredados."""
    total_capas = (
        CapaCosto.objects.filter(lote=lote).aggregate(
            total=Sum("cantidad_restante")
        )["total"]
        or Decimal("0.00")
    )
    diferencia = lote.stock_actual - total_capas
    if diferencia < 0:
        raise ValidationError(
            f"El historial de costos del lote {lote.codigo_lote} excede "
            "su stock actual. Revisa el inventario antes de vender."
        )
    if diferencia > 0:
        CapaCosto.objects.create(
            lote=lote,
            cantidad_inicial=diferencia,
            cantidad_restante=diferencia,
            costo_unitario=None,
        )

    capas = list(
        CapaCosto.objects.select_for_update()
        .filter(lote=lote, cantidad_restante__gt=0)
        .order_by("creado_en", "pk")
    )
    restante = cantidad
    asignaciones = []
    for capa in capas:
        aplicado = min(restante, capa.cantidad_restante)
        if aplicado > 0:
            asignaciones.append(
                {
                    "capa": capa,
                    "cantidad": aplicado,
                    "costo_unitario": capa.costo_unitario,
                }
            )
            restante -= aplicado
        if restante == 0:
            break
    if restante > 0:
        raise ValidationError(
            f"No se pudo asignar el costo de las existencias del lote "
            f"{lote.codigo_lote}."
        )
    return asignaciones


@transaction.atomic
def registrar_costo_existencia(
    *, lote: Lote, costo_unitario, usuario, motivo: str = ""
) -> AjusteCostoInventario:
    """Completa el costo faltante de unidades ya existentes sin tocar el stock."""
    _validar_usuario(usuario)
    if lote is None or not lote.pk:
        raise ValidationError("Selecciona el lote que se va a valorizar.")
    costo_unitario = _validar_costo(costo_unitario)
    if costo_unitario is None:
        raise ValidationError("Ingresa el costo unitario de adquisición.")

    lote = Lote.objects.select_for_update().get(pk=lote.pk)
    capas = list(
        CapaCosto.objects.select_for_update().filter(
            lote=lote,
            cantidad_restante__gt=0,
            costo_unitario__isnull=True,
        )
    )
    cantidad = sum(
        (capa.cantidad_restante for capa in capas), Decimal("0.00")
    )
    if cantidad <= 0:
        raise ValidationError(
            "Este lote no tiene unidades disponibles pendientes de costeo."
        )

    for capa in capas:
        capa.costo_unitario = costo_unitario
        capa.save(update_fields=["costo_unitario"])

    return AjusteCostoInventario.objects.create(
        lote=lote,
        usuario=usuario,
        cantidad=cantidad,
        costo_unitario=costo_unitario,
        motivo=" ".join((motivo or "Costeo de existencias iniciales.").split()),
    )


@transaction.atomic
def crear_lote(
    *,
    producto,
    codigo_lote: str,
    fecha_fabricacion=None,
    fecha_vencimiento=None,
    fecha_ingreso=None,
    stock_inicial=Decimal("0.00"),
    costo_unitario=None,
    activo: bool = True,
    usuario,
    motivo: str = "",
) -> Lote:
    """Crea un lote y, si tiene stock inicial, registra el movimiento INICIAL."""
    _validar_usuario(usuario)

    if producto is None:
        raise ValidationError("Selecciona el producto del lote.")
    if not producto.activo:
        raise ValidationError(
            "No puedes crear un lote para un producto inactivo."
        )

    stock_inicial = _decimal(
        stock_inicial, "El stock inicial no es válido."
    )
    costo_unitario = _validar_costo(costo_unitario)
    if stock_inicial < Decimal("0.00"):
        raise ValidationError("El stock inicial no puede ser negativo.")
    if stock_inicial > STOCK_MAXIMO:
        raise ValidationError("El stock inicial excede el máximo permitido.")
    if stock_inicial != stock_inicial.quantize(Decimal("0.01")):
        raise ValidationError(
            "El stock inicial admite como máximo dos decimales."
        )
    if stock_inicial > 0 and costo_unitario is None:
        raise ValidationError(
            "Ingresa el costo unitario de adquisición del stock inicial."
        )

    lote = Lote(
        producto=producto,
        codigo_lote=codigo_lote,
        fecha_fabricacion=fecha_fabricacion,
        fecha_vencimiento=fecha_vencimiento,
        fecha_ingreso=fecha_ingreso or timezone.localdate(),
        stock_actual=Decimal("0.00"),
        activo=activo,
    )
    lote.full_clean()
    lote.save()

    if stock_inicial > Decimal("0.00"):
        _aplicar_movimiento(
            lote,
            tipo=MovimientoInventario.Tipo.INICIAL,
            cantidad=stock_inicial,
            usuario=usuario,
            motivo=motivo or "Carga inicial del lote.",
            costo_unitario=costo_unitario,
        )
        lote.refresh_from_db()

    return lote


@transaction.atomic
def registrar_movimiento(
    *,
    lote: Lote,
    tipo: str,
    cantidad,
    usuario,
    motivo: str = "",
    costo_unitario=None,
) -> MovimientoInventario:
    """Registra una entrada, salida o ajuste sobre un lote activo.

    El lote se bloquea dentro de la transacción para evitar que dos
    operaciones simultáneas calculen el stock resultante sobre el mismo valor.
    """
    _validar_usuario(usuario)

    if lote is None or not lote.pk:
        raise ValidationError("Selecciona el lote que se va a modificar.")
    if tipo not in TIPOS_MANUALES:
        raise ValidationError(
            "El tipo de movimiento no está disponible. El inventario inicial "
            "se registra al crear el lote."
        )

    cantidad = _validar_cantidad(cantidad)
    costo_unitario = _validar_costo(costo_unitario)
    if tipo in MovimientoInventario.TIPOS_ENTRADA and costo_unitario is None:
        raise ValidationError(
            "Registra el costo unitario de adquisición para esta entrada."
        )

    lote = (
        Lote.objects.select_for_update()
        .select_related("producto")
        .get(pk=lote.pk)
    )
    if not lote.activo:
        raise ValidationError(
            "No puedes registrar movimientos en un lote inactivo."
        )

    return _aplicar_movimiento(
        lote,
        tipo=tipo,
        cantidad=cantidad,
        usuario=usuario,
        motivo=motivo,
        costo_unitario=costo_unitario,
    )


@transaction.atomic
def consumir_stock_producto(
    *, producto, cantidad, usuario, detalle_venta
) -> Decimal | None:
    """Consume lotes FEFO y aplica FIFO por costo dentro de cada lote."""
    _validar_usuario(usuario)
    if producto is None or not producto.pk:
        raise ValidationError("Selecciona un producto para descontar stock.")
    cantidad = _validar_cantidad(cantidad)
    if cantidad != cantidad.to_integral_value():
        raise ValidationError("La cantidad vendida debe ser un número entero.")

    hoy = timezone.localdate()
    lotes = list(
        Lote.objects.select_for_update()
        .filter(producto=producto, activo=True, stock_actual__gt=0)
        .filter(
            Q(fecha_vencimiento__isnull=True)
            | Q(fecha_vencimiento__gte=hoy)
        )
        .order_by(
            F("fecha_vencimiento").asc(nulls_last=True),
            "fecha_ingreso",
            "pk",
        )
    )
    disponible = sum(
        (lote.stock_actual for lote in lotes), Decimal("0.00")
    )
    if disponible < cantidad:
        raise ValidationError(
            f"Stock insuficiente de {producto.nombre}. Disponible: "
            f"{disponible:.2f}; solicitado: {cantidad:.2f}."
        )

    restante = cantidad
    costo_total = Decimal("0.00")
    costo_completo = True
    for lote in lotes:
        aplicado = min(restante, lote.stock_actual)
        if aplicado <= 0:
            continue
        asignaciones = _preparar_asignaciones(lote, aplicado)
        movimiento = _aplicar_movimiento(
            lote,
            tipo=MovimientoInventario.Tipo.SALIDA,
            cantidad=aplicado,
            usuario=usuario,
            motivo=f"Venta {detalle_venta.venta.numero}",
            detalle_venta=detalle_venta,
            asignaciones_costo=asignaciones,
        )
        if movimiento.costo_total is None:
            costo_completo = False
        else:
            costo_total += movimiento.costo_total
        restante -= aplicado
        if restante == 0:
            break

    return costo_total.quantize(Decimal("0.01")) if costo_completo else None
