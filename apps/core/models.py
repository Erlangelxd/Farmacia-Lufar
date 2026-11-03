"""Modelos del núcleo.

El núcleo no define entidades de negocio. Solo conserva la configuración
general del sistema, que es infraestructura compartida por todas las apps.
"""

from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models


class ConfiguracionSistema(models.Model):
    """Datos generales de la farmacia usados en la interfaz y los reportes."""

    nombre_empresa = models.CharField(
        "nombre de la empresa", max_length=150, default="Farmacia Lufar"
    )
    nit = models.CharField("NIT", max_length=30, blank=True)
    direccion = models.CharField("dirección", max_length=200, blank=True)
    telefono = models.CharField("teléfono", max_length=30, blank=True)
    email = models.EmailField("correo electrónico", blank=True)
    moneda = models.CharField("moneda", max_length=10, default="BOB")
    impuesto_porcentaje = models.DecimalField(
        "impuesto (%)",
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    logo = models.FileField(
        "logotipo",
        upload_to="configuracion/",
        blank=True,
    )
    stock_minimo_default = models.PositiveIntegerField(
        "stock mínimo por defecto",
        default=5,
    )
    actualizado_en = models.DateTimeField("última actualización", auto_now=True)

    class Meta:
        verbose_name = "configuración del sistema"
        verbose_name_plural = "configuración del sistema"

    def __str__(self) -> str:
        return self.nombre_empresa

    def save(self, *args, **kwargs):
        """Mantiene una sola fila lógica de configuración."""
        self.pk = 1
        self.nombre_empresa = " ".join((self.nombre_empresa or "").split())
        self.nit = (self.nit or "").strip().upper()
        super().save(*args, **kwargs)
