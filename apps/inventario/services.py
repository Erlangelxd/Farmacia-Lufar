"""Servicios transaccionales de inventario.

Toda alteración de existencias pasa por este módulo. El servicio actualiza el
stock del lote y registra un movimiento inmutable dentro de la misma
transacción, de modo que el historial siempre pueda reconstruirse.
"""

from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from .models import Lote, MovimientoInventario

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

    lote.stock_actual = nuevo_stock
    lote.save(update_fields=["stock_actual", "actualizado_en"])

    return MovimientoInventario.objects.create(
        lote=lote,
        tipo=tipo,
        cantidad=cantidad,
        stock_resultante=nuevo_stock,
        detalle_venta=detalle_venta,
        motivo=motivo,
        usuario=usuario,
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
    if stock_inicial < Decimal("0.00"):
        raise ValidationError("El stock inicial no puede ser negativo.")
    if stock_inicial > STOCK_MAXIMO:
        raise ValidationError("El stock inicial excede el máximo permitido.")
    if stock_inicial != stock_inicial.quantize(Decimal("0.01")):
        raise ValidationError(
            "El stock inicial admite como máximo dos decimales."
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
    )
