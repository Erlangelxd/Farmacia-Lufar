"""Consultas reutilizables de existencias de inventario."""

from decimal import Decimal

from django.db.models import DecimalField, F, Q, Sum
from django.db.models.functions import Coalesce

from apps.catalogo.models import Producto


def stock_por_producto():
    """Expresión con la suma del stock de los lotes activos de un producto."""
    return Coalesce(
        Sum("lotes__stock_actual", filter=Q(lotes__activo=True)),
        Decimal("0.00"),
        output_field=DecimalField(max_digits=12, decimal_places=2),
    )


def productos_con_stock_bajo():
    """Productos activos cuyo stock total no supera su stock mínimo."""
    return (
        Producto.objects.filter(activo=True)
        .annotate(stock_total=stock_por_producto())
        .filter(stock_total__lte=F("stock_minimo"))
    )
