"""Modelos de inventario.

La app es la única dueña del stock: las compras y las ventas no modifican
existencias directamente, sino que registran movimientos a través de los
servicios transaccionales correspondientes.
"""

from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone


class Lote(models.Model):
    """Lote de un producto con su existencia y fecha de vencimiento."""

    producto = models.ForeignKey(
        "catalogo.Producto",
        verbose_name="producto",
        on_delete=models.PROTECT,
        related_name="lotes",
    )
    codigo_lote = models.CharField("código de lote", max_length=50)
    fecha_fabricacion = models.DateField(
        "fecha de fabricación", null=True, blank=True
    )
    fecha_vencimiento = models.DateField(
        "fecha de vencimiento", null=True, blank=True
    )
    fecha_ingreso = models.DateField("fecha de ingreso", default=timezone.localdate)
    stock_actual = models.DecimalField(
        "stock actual",
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    activo = models.BooleanField("lote activo", default=True)
    creado_en = models.DateTimeField("fecha de registro", auto_now_add=True)
    actualizado_en = models.DateTimeField("última actualización", auto_now=True)

    class Meta:
        verbose_name = "lote"
        verbose_name_plural = "lotes"
        ordering = ("fecha_vencimiento", "pk")
        indexes = (
            models.Index(
                fields=("producto", "fecha_vencimiento"),
                name="inventario_lote_prod_venc_idx",
            ),
        )
        constraints = (
            models.UniqueConstraint(
                fields=("producto", "codigo_lote"),
                name="inventario_lote_unico_por_producto",
                violation_error_message=(
                    "El producto ya tiene un lote con ese código."
                ),
            ),
            models.CheckConstraint(
                condition=Q(stock_actual__gte=0),
                name="inventario_lote_stock_no_negativo",
            ),
        )

    def __str__(self) -> str:
        return f"{self.producto} — lote {self.codigo_lote}"


class MovimientoInventario(models.Model):
    """Movimiento inmutable que explica cada cambio de existencias."""

    class Tipo(models.TextChoices):
        INICIAL = "INICIAL", "Inventario inicial"
        ENTRADA = "ENTRADA", "Entrada"
        SALIDA = "SALIDA", "Salida"
        AJUSTE_POSITIVO = "AJUSTE_POSITIVO", "Ajuste positivo"
        AJUSTE_NEGATIVO = "AJUSTE_NEGATIVO", "Ajuste negativo"

    lote = models.ForeignKey(
        Lote,
        verbose_name="lote",
        on_delete=models.PROTECT,
        related_name="movimientos",
    )
    tipo = models.CharField("tipo", max_length=20, choices=Tipo.choices)
    cantidad = models.DecimalField(
        "cantidad",
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    stock_resultante = models.DecimalField(
        "stock resultante",
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    detalle_venta = models.ForeignKey(
        "ventas.DetalleVenta",
        verbose_name="detalle de venta",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="movimientos_inventario",
    )
    motivo = models.CharField("motivo", max_length=200, blank=True)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="registrado por",
        on_delete=models.PROTECT,
        related_name="movimientos_inventario",
    )
    fecha = models.DateTimeField("fecha", default=timezone.now)

    class Meta:
        verbose_name = "movimiento de inventario"
        verbose_name_plural = "movimientos de inventario"
        ordering = ("-fecha", "-pk")
        indexes = (
            models.Index(
                fields=("lote", "fecha"), name="inventario_mov_lote_fecha_idx"
            ),
            models.Index(fields=("fecha",), name="inventario_mov_fecha_idx"),
        )
        constraints = (
            models.CheckConstraint(
                condition=Q(cantidad__gt=0),
                name="inventario_mov_cantidad_positiva",
            ),
            models.CheckConstraint(
                condition=Q(stock_resultante__gte=0),
                name="inventario_mov_stock_no_negativo",
            ),
        )

    def __str__(self) -> str:
        return f"{self.get_tipo_display()} — {self.lote}"
