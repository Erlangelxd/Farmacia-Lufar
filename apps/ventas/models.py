"""Modelos del módulo de ventas."""

from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import F, Q


class Venta(models.Model):
    """Venta confirmada de productos.

    En esta etapa la venta es inmutable: no se edita ni se elimina desde la
    interfaz. El stock se integrará cuando exista el módulo de inventario.
    """

    class MetodoPago(models.TextChoices):
        EFECTIVO = "EFECTIVO", "Efectivo"

    cliente = models.ForeignKey(
        "clientes.Cliente",
        verbose_name="cliente",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="ventas",
    )
    vendedor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="vendedor",
        on_delete=models.PROTECT,
        related_name="ventas_realizadas",
    )
    metodo_pago = models.CharField(
        "método de pago",
        max_length=20,
        choices=MetodoPago.choices,
        default=MetodoPago.EFECTIVO,
    )
    monto_recibido = models.DecimalField(
        "monto recibido",
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    total = models.DecimalField(
        "total",
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    creado_en = models.DateTimeField(
        "fecha de venta",
        auto_now_add=True,
    )

    class Meta:
        verbose_name = "venta"
        verbose_name_plural = "ventas"
        ordering = ("-creado_en", "-pk")
        constraints = (
            models.CheckConstraint(
                condition=Q(total__gte=0),
                name="ventas_total_no_negativo",
            ),
            models.CheckConstraint(
                condition=Q(monto_recibido__gte=0),
                name="ventas_monto_recibido_no_negativo",
            ),
            models.CheckConstraint(
                condition=Q(monto_recibido__gte=F("total")),
                name="ventas_monto_recibido_cubre_total",
            ),
        )

    @property
    def numero(self) -> str:
        """Número visible y estable de la venta."""
        if not self.pk:
            return "Sin número"
        return f"V-{self.pk:06d}"

    @property
    def cambio(self) -> Decimal:
        """Diferencia entre el efectivo recibido y el total."""
        return (self.monto_recibido or Decimal("0.00")) - (
            self.total or Decimal("0.00")
        )

    @property
    def cantidad_productos(self) -> int:
        """Cantidad total de unidades vendidas."""
        if not self.pk:
            return 0
        return sum(detalle.cantidad for detalle in self.detalles.all())

    def __str__(self) -> str:
        cliente = self.cliente.nombre if self.cliente_id else "Consumidor final"
        return f"{self.numero} — {cliente}"


class DetalleVenta(models.Model):
    """Línea de producto de una venta.

    Guarda una copia del código, nombre y precio del producto para conservar el
    historial aunque el catálogo cambie posteriormente.
    """

    venta = models.ForeignKey(
        Venta,
        verbose_name="venta",
        on_delete=models.CASCADE,
        related_name="detalles",
    )
    producto = models.ForeignKey(
        "catalogo.Producto",
        verbose_name="producto",
        on_delete=models.PROTECT,
        related_name="detalles_venta",
    )
    codigo_producto = models.CharField(
        "código del producto",
        max_length=30,
    )
    nombre_producto = models.CharField(
        "nombre del producto",
        max_length=150,
    )
    cantidad = models.PositiveIntegerField(
        "cantidad",
        validators=[
            MinValueValidator(1),
            MaxValueValidator(9999),
        ],
    )
    precio_unitario = models.DecimalField(
        "precio unitario",
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    creado_en = models.DateTimeField(
        "fecha de registro",
        auto_now_add=True,
    )

    class Meta:
        verbose_name = "detalle de venta"
        verbose_name_plural = "detalles de venta"
        ordering = ("pk",)
        constraints = (
            models.CheckConstraint(
                condition=Q(cantidad__gt=0),
                name="ventas_detalle_cantidad_positiva",
            ),
            models.CheckConstraint(
                condition=Q(precio_unitario__gte=0),
                name="ventas_detalle_precio_no_negativo",
            ),
            models.UniqueConstraint(
                fields=("venta", "producto"),
                name="ventas_detalle_producto_unico_por_venta",
            ),
        )

    @property
    def subtotal(self) -> Decimal:
        """Importe de la línea."""
        return (self.precio_unitario or Decimal("0.00")) * self.cantidad

    def __str__(self) -> str:
        return f"{self.nombre_producto} x {self.cantidad}"
