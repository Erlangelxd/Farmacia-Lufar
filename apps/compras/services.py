"""Servicios transaccionales del módulo de compras.

El alta y la edición de compras calculan los totales en el servidor. La
recepción genera una entrada de inventario por cada línea usando los servicios
de ``inventario``; nunca modifica ``Lote.stock_actual`` directamente.
"""

from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.inventario.models import MovimientoInventario
from apps.inventario.services import registrar_movimiento

from .models import Compra, DetalleCompra

TOTAL_MAXIMO = Decimal("9999999999.99")
COSTO_MAXIMO = Decimal("99999999.99")
CANTIDAD_MAXIMA = 9999


def _decimal(valor, mensaje: str) -> Decimal:
    """Convierte un valor a ``Decimal`` y devuelve un error legible."""
    try:
        return Decimal(str(valor))
    except (InvalidOperation, TypeError, ValueError):
        raise ValidationError(mensaje) from None


def _validar_usuario(usuario) -> None:
    if usuario is None or not getattr(usuario, "is_authenticated", False):
        raise ValidationError(
            "Se requiere un usuario autenticado para registrar la compra."
        )


def _validar_lineas(lineas: list[dict]) -> tuple[list[tuple], Decimal]:
    """Valida las líneas y devuelve los datos normalizados y el subtotal."""
    lineas = list(lineas)
    if not lineas:
        raise ValidationError("Agrega al menos un producto a la compra.")

    validadas: list[tuple] = []
    subtotal = Decimal("0.00")

    for indice, linea in enumerate(lineas, start=1):
        producto = linea.get("producto")
        cantidad = linea.get("cantidad")
        costo = linea.get("costo_unitario")

        if producto is None:
            raise ValidationError(
                f"Selecciona el producto de la línea {indice}."
            )
        if not producto.activo:
            raise ValidationError(
                f"El producto {producto.nombre} no está activo."
            )

        try:
            cantidad = int(cantidad)
        except (TypeError, ValueError):
            raise ValidationError(
                "La cantidad debe ser un número entero."
            ) from None

        if cantidad <= 0:
            raise ValidationError("La cantidad debe ser mayor que cero.")
        if cantidad > CANTIDAD_MAXIMA:
            raise ValidationError(
                f"La cantidad no puede superar {CANTIDAD_MAXIMA} unidades."
            )

        costo = _decimal(costo, "El costo unitario no es válido.")
        if costo < Decimal("0.00"):
            raise ValidationError("El costo unitario no puede ser negativo.")
        if costo > COSTO_MAXIMO:
            raise ValidationError(
                "El costo unitario excede el máximo permitido."
            )
        if costo != costo.quantize(Decimal("0.01")):
            raise ValidationError(
                "El costo unitario admite como máximo dos decimales."
            )

        linea_subtotal = costo * cantidad
        subtotal += linea_subtotal
        if subtotal > TOTAL_MAXIMO:
            raise ValidationError(
                "El subtotal de la compra excede el máximo permitido."
            )

        validadas.append((producto, cantidad, costo, linea_subtotal))

    return validadas, subtotal


def _validar_impuesto(impuesto) -> Decimal:
    impuesto = _decimal(
        impuesto if impuesto is not None else Decimal("0.00"),
        "El impuesto no es válido.",
    )
    if impuesto < Decimal("0.00"):
        raise ValidationError("El impuesto no puede ser negativo.")
    if impuesto > TOTAL_MAXIMO:
        raise ValidationError("El impuesto excede el máximo permitido.")
    if impuesto != impuesto.quantize(Decimal("0.01")):
        raise ValidationError("El impuesto admite como máximo dos decimales.")
    return impuesto


def _validar_total(subtotal: Decimal, impuesto: Decimal) -> Decimal:
    total = subtotal + impuesto
    if total > TOTAL_MAXIMO:
        raise ValidationError("El total de la compra excede el máximo permitido.")
    return total


def _crear_detalles(compra: Compra, lineas: list[tuple]) -> None:
    """Crea las líneas de la compra con su subtotal ya calculado."""
    DetalleCompra.objects.bulk_create(
        [
            DetalleCompra(
                compra=compra,
                producto=producto,
                cantidad=cantidad,
                costo_unitario=costo,
                subtotal=linea_subtotal,
            )
            for producto, cantidad, costo, linea_subtotal in lineas
        ]
    )


@transaction.atomic
def registrar_compra(
    *,
    proveedor,
    usuario,
    numero_factura: str = "",
    fecha_compra=None,
    impuesto=Decimal("0.00"),
    observaciones: str = "",
    lineas: list[dict],
) -> Compra:
    """Registra una compra en borrador con sus detalles."""
    _validar_usuario(usuario)

    if proveedor is None:
        raise ValidationError("Selecciona el proveedor de la compra.")
    if not proveedor.activo:
        raise ValidationError("El proveedor seleccionado no está activo.")

    lineas_validadas, subtotal = _validar_lineas(lineas)
    impuesto = _validar_impuesto(impuesto)
    total = _validar_total(subtotal, impuesto)

    compra = Compra.objects.create(
        proveedor=proveedor,
        usuario=usuario,
        numero_factura=numero_factura,
        fecha_compra=fecha_compra or timezone.localdate(),
        estado=Compra.Estado.BORRADOR,
        subtotal=subtotal,
        impuesto=impuesto,
        total=total,
        observaciones=observaciones,
    )
    _crear_detalles(compra, lineas_validadas)
    return compra


@transaction.atomic
def actualizar_compra(
    *,
    compra: Compra,
    proveedor,
    numero_factura: str = "",
    fecha_compra=None,
    impuesto=Decimal("0.00"),
    observaciones: str = "",
    lineas: list[dict],
) -> Compra:
    """Actualiza una compra en borrador y reemplaza sus líneas."""
    if compra is None or not compra.pk:
        raise ValidationError("Selecciona la compra que se va a actualizar.")

    compra = Compra.objects.select_for_update().get(pk=compra.pk)
    if compra.estado != Compra.Estado.BORRADOR:
        raise ValidationError("Solo puedes editar compras en borrador.")

    if proveedor is None:
        raise ValidationError("Selecciona el proveedor de la compra.")
    if proveedor.pk != compra.proveedor_id and not proveedor.activo:
        raise ValidationError("El proveedor seleccionado no está activo.")

    lineas_validadas, subtotal = _validar_lineas(lineas)
    impuesto = _validar_impuesto(impuesto)
    total = _validar_total(subtotal, impuesto)

    compra.proveedor = proveedor
    compra.numero_factura = numero_factura
    compra.fecha_compra = fecha_compra or compra.fecha_compra
    compra.subtotal = subtotal
    compra.impuesto = impuesto
    compra.total = total
    compra.observaciones = observaciones
    compra.save(
        update_fields=[
            "proveedor",
            "numero_factura",
            "fecha_compra",
            "subtotal",
            "impuesto",
            "total",
            "observaciones",
            "actualizado_en",
        ]
    )

    compra.detalles.all().delete()
    _crear_detalles(compra, lineas_validadas)
    return compra


@transaction.atomic
def recibir_compra(
    *,
    compra: Compra,
    usuario,
    lotes_por_detalle: dict,
) -> Compra:
    """Recibe una compra en borrador y registra las entradas de inventario.

    ``lotes_por_detalle`` asocia el ``pk`` de cada detalle con el lote existente
    que recibirá la mercadería. La operación es atómica: si una línea falla,
    ninguna entrada de inventario queda registrada.
    """
    _validar_usuario(usuario)

    if compra is None or not compra.pk:
        raise ValidationError("Selecciona la compra que se va a recibir.")

    compra = Compra.objects.select_for_update().get(pk=compra.pk)
    if compra.estado != Compra.Estado.BORRADOR:
        raise ValidationError("Solo puedes recibir compras en borrador.")

    mapa_lotes = {
        int(clave): lote
        for clave, lote in (lotes_por_detalle or {}).items()
    }
    detalles = list(compra.detalles.select_related("producto"))
    if not detalles:
        raise ValidationError("La compra no tiene productos para recibir.")

    lotes_vistos: set[int] = set()
    for detalle in detalles:
        lote = mapa_lotes.get(detalle.pk)
        if lote is None:
            raise ValidationError(
                f"Selecciona un lote para {detalle.producto.nombre}."
            )
        if lote.producto_id != detalle.producto_id:
            raise ValidationError(
                f"El lote {lote.codigo_lote} no pertenece a "
                f"{detalle.producto.nombre}."
            )
        if not lote.activo:
            raise ValidationError(
                f"El lote {lote.codigo_lote} no está activo."
            )
        if lote.pk in lotes_vistos:
            raise ValidationError(
                f"El lote {lote.codigo_lote} está repetido en la recepción."
            )
        lotes_vistos.add(lote.pk)

    for detalle in detalles:
        lote = mapa_lotes[detalle.pk]
        registrar_movimiento(
            lote=lote,
            tipo=MovimientoInventario.Tipo.ENTRADA,
            cantidad=detalle.cantidad,
            usuario=usuario,
            motivo=f"Recepción de compra {compra.numero}",
            costo_unitario=detalle.costo_unitario,
        )
        detalle.lote = lote
        detalle.save(update_fields=["lote"])

    compra.estado = Compra.Estado.RECIBIDA
    compra.fecha_recepcion = timezone.localdate()
    compra.save(
        update_fields=["estado", "fecha_recepcion", "actualizado_en"]
    )
    return compra


@transaction.atomic
def anular_compra(*, compra: Compra) -> Compra:
    """Anula una compra en borrador sin afectar inventario."""
    if compra is None or not compra.pk:
        raise ValidationError("Selecciona la compra que se va a anular.")

    compra = Compra.objects.select_for_update().get(pk=compra.pk)
    if compra.estado != Compra.Estado.BORRADOR:
        raise ValidationError("Solo puedes anular compras en borrador.")

    compra.estado = Compra.Estado.ANULADA
    compra.save(update_fields=["estado", "actualizado_en"])
    return compra
