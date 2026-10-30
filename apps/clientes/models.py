"""Modelos del módulo de clientes."""

from django.conf import settings
from django.db import models
from django.db.models import Q


class Cliente(models.Model):
    """Persona o empresa que compra en la farmacia.

    En esta etapa se registran los datos mínimos de identificación y contacto.
    El historial comercial se incorporará cuando exista el módulo de ventas.
    """

    class TipoDocumento(models.TextChoices):
        CI = "CI", "Cédula de Identidad"
        NIT = "NIT", "NIT"
        PASAPORTE = "PASAPORTE", "Pasaporte"
        OTRO = "OTRO", "Otro"

    nombre = models.CharField(
        "nombre completo o razón social",
        max_length=150,
    )
    tipo_documento = models.CharField(
        "tipo de documento",
        max_length=20,
        choices=TipoDocumento.choices,
        blank=True,
    )
    numero_documento = models.CharField(
        "número de documento",
        max_length=30,
        blank=True,
    )
    telefono = models.CharField(
        "teléfono",
        max_length=30,
        blank=True,
    )
    activo = models.BooleanField(
        "cliente activo",
        default=True,
    )
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="registrado por",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="clientes_registrados",
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
        verbose_name = "cliente"
        verbose_name_plural = "clientes"
        ordering = ("nombre", "pk")
        constraints = (
            models.CheckConstraint(
                condition=(
                    Q(tipo_documento="", numero_documento="")
                    | (~Q(tipo_documento="") & ~Q(numero_documento=""))
                ),
                name="clientes_documento_tipo_numero_coherentes",
                violation_error_message=(
                    "El tipo y el número de documento deben registrarse juntos."
                ),
            ),
            models.UniqueConstraint(
                fields=("tipo_documento", "numero_documento"),
                condition=~Q(numero_documento="") & ~Q(tipo_documento=""),
                name="clientes_documento_unico_por_tipo",
                violation_error_message=(
                    "Ya existe un cliente con ese tipo y número de documento."
                ),
            ),
        )

    def __str__(self) -> str:
        documento = " ".join(
            parte
            for parte in (
                self.get_tipo_documento_display(),
                self.numero_documento,
            )
            if parte
        )
        if documento:
            return f"{self.nombre} ({documento})"
        return self.nombre

    def save(self, *args, **kwargs):
        """Normaliza espacios antes de guardar."""
        self.nombre = " ".join((self.nombre or "").split())
        self.tipo_documento = (self.tipo_documento or "").strip()
        self.numero_documento = (self.numero_documento or "").strip()
        self.telefono = (self.telefono or "").strip()
        super().save(*args, **kwargs)
