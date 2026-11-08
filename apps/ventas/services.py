"""Servicios transaccionales del módulo de ventas."""

from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.inventario.services import consumir_stock_producto

from .models import DetalleVenta, Venta

TOTAL_MAXIMO = Decimal("9999999999.99")


def _decimal(valor, mensaje: str) -> Decimal:
    """Convierte un valor a Decimal y devuelve un error legible si no es válido."""
    try:
        return Decimal(str(valor))
    except (InvalidOperation, TypeError, ValueError):
        raise ValidationError(mensaje) from None


def registrar_venta(
    *,
    vendedor,
    cliente,
    metodo_pago: str,
    monto_recibido,
    lineas: list[dict],
) -> Venta:
    """Registra una venta y sus detalles dentro de una sola transacción.

    ``lineas`` debe contener diccionarios con las claves ``producto`` y
    ``cantidad``. El precio siempre se toma del catálogo y el inventario se
    consume por FEFO; el costo real queda guardado en el detalle.
    """
    lineas = list(lineas)
    if not lineas:
        raise ValidationError("Agrega al menos un producto a la venta.")

    if metodo_pago != Venta.MetodoPago.EFECTIVO:
        raise ValidationError("El método de pago seleccionado no está disponible.")

    if cliente is not None and not cliente.activo:
        raise ValidationError("El cliente seleccionado no está activo.")

    monto = _decimal(monto_recibido, "El monto recibido no es válido.")
    if monto < 0:
        raise ValidationError("El monto recibido no puede ser negativo.")

    productos_vistos: set[int] = set()
    lineas_validadas: list[tuple[object, int]] = []
    total = Decimal("0.00")

    for linea in lineas:
        producto = linea.get("producto")
        cantidad = linea.get("cantidad")

        if producto is None:
            raise ValidationError("Selecciona un producto en cada línea.")

        if not producto.activo:
            raise ValidationError(
                f"El producto {producto.nombre} no está activo."
            )
        if producto.precio_venta < 0:
            raise ValidationError(
                f"El producto {producto.nombre} tiene un precio inválido."
            )

        try:
            cantidad = int(cantidad)
        except (TypeError, ValueError):
            raise ValidationError(
                "La cantidad debe ser un número entero."
            ) from None

        if cantidad <= 0:
            raise ValidationError("La cantidad debe ser mayor que cero.")
        if cantidad > 9999:
            raise ValidationError("La cantidad no puede superar 9999 unidades.")
        if producto.pk in productos_vistos:
            raise ValidationError(
                f"El producto {producto.nombre} está repetido en la venta."
            )

        productos_vistos.add(producto.pk)
        lineas_validadas.append((producto, cantidad))
        total += producto.precio_venta * cantidad

    if total > TOTAL_MAXIMO:
        raise ValidationError("El total de la venta excede el máximo permitido.")
    if monto < total:
        raise ValidationError(
            "El monto recibido no cubre el total de la venta."
        )

    with transaction.atomic():
        venta = Venta.objects.create(
            cliente=cliente,
            vendedor=vendedor,
            metodo_pago=metodo_pago,
            monto_recibido=monto,
            total=total,
        )
        for producto, cantidad in lineas_validadas:
            detalle = DetalleVenta.objects.create(
                venta=venta,
                producto=producto,
                codigo_producto=producto.codigo,
                nombre_producto=producto.nombre,
                cantidad=cantidad,
                precio_unitario=producto.precio_venta,
            )
            detalle.costo_total = consumir_stock_producto(
                producto=producto,
                cantidad=cantidad,
                usuario=vendedor,
                detalle_venta=detalle,
            )
            detalle.save(update_fields=["costo_total"])

    return venta
