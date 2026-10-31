"""Modelos del catálogo de productos."""

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models


class Producto(models.Model):
    """Producto mínimo necesario para registrar ventas.

    En esta etapa solo se administran los datos que usa el módulo de ventas.
    Categorías, proveedores, presentaciones, imágenes y stock se incorporarán
    cuando se implemente el catálogo completo y el inventario.
    """

    codigo = models.CharField(
        "código",
        max_length=30,
        unique=True,
    )
    nombre = models.CharField(
        "nombre",
        max_length=150,
    )
    precio_venta = models.DecimalField(
        "precio de venta",
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    activo = models.BooleanField(
        "producto activo",
        default=True,
    )
    creado_en = models.DateTimeField(
        "fecha de registro",
        auto_now_add=True,
    )
    actualizado_en = models.DateTimeField(
        "última actualización",
        auto_now=True,
    )

    class Meta:
        verbose_name = "producto"
        verbose_name_plural = "productos"
        ordering = ("nombre", "pk")

    def __str__(self) -> str:
        return f"{self.codigo} — {self.nombre}"

    def clean(self):
        """Normaliza los datos y evita códigos duplicados sin distinguir mayúsculas."""
        super().clean()
        self.codigo = (self.codigo or "").strip().upper()
        self.nombre = " ".join((self.nombre or "").split())

        if self.codigo and Producto.objects.filter(
            codigo__iexact=self.codigo
        ).exclude(pk=self.pk).exists():
            raise ValidationError(
                {"codigo": "Ya existe un producto con ese código."}
            )

    def save(self, *args, **kwargs):
        """Normaliza el código y el nombre antes de guardar."""
        self.codigo = (self.codigo or "").strip().upper()
        self.nombre = " ".join((self.nombre or "").split())
        super().save(*args, **kwargs)
