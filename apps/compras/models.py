"""Modelos de compras.

Proveedor se mantiene en esta app para respetar las ocho aplicaciones del
alcance inicial y evitar una novena app sin necesidad.
"""

from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone


class Proveedor(models.Model):
    """Empresa o persona que abastece productos a la farmacia."""

    nombre = models.CharField("nombre o razón social", max_length=150)
    nit = models.CharField("NIT", max_length=30, blank=True)
    telefono = models.CharField("teléfono", max_length=30, blank=True)
    email = models.EmailField("correo electrónico", blank=True)
    direccion = models.CharField("dirección", max_length=200, blank=True)
    contacto = models.CharField("persona de contacto", max_length=120, blank=True)
    activo = models.BooleanField("proveedor activo", default=True)
    creado_en = models.DateTimeField("fecha de registro", auto_now_add=True)
    actualizado_en = models.DateTimeField("última actualización", auto_now=True)

    class Meta:
        verbose_name = "proveedor"
        verbose_name_plural = "proveedores"
        ordering = ("nombre", "pk")
        constraints = (
            models.UniqueConstraint(
                fields=("nit",),
                condition=~Q(nit=""),
                name="compras_proveedor_nit_unico",
                violation_error_message=(
                    "Ya existe un proveedor con ese NIT."
                ),
            ),
        )

    def __str__(self) -> str:
        return self.nombre

    def clean(self):
        """Normaliza los datos y valida que el NIT no se repita."""
        super().clean()
        self.nombre = " ".join((self.nombre or "").split())
        self.nit = (self.nit or "").strip().upper()
        self.telefono = (self.telefono or "").strip()
        self.email = (self.email or "").strip()
        self.direccion = " ".join((self.direccion or "").split())
        self.contacto = " ".join((self.contacto or "").split())

        if not self.nombre:
            raise ValidationError(
                {"nombre": "Ingresa el nombre o razón social."}
            )

        if self.nit:
            duplicados = Proveedor.objects.filter(nit__iexact=self.nit)
            if self.pk:
                duplicados = duplicados.exclude(pk=self.pk)
            if duplicados.exists():
                raise ValidationError(
                    {"nit": "Ya existe un proveedor con ese NIT."}
                )

    def save(self, *args, **kwargs):
        self.nombre = " ".join((self.nombre or "").split())
        self.nit = (self.nit or "").strip().upper()
        self.telefono = (self.telefono or "").strip()
        self.email = (self.email or "").strip()
        self.direccion = " ".join((self.direccion or "").split())
        self.contacto = " ".join((self.contacto or "").split())
        super().save(*args, **kwargs)


class Compra(models.Model):
    """Documento de compra a un proveedor.

    Solo una compra en estado ``RECIBIDA`` genera movimientos de entrada en el
    inventario; el estado ``BORRADOR`` no afecta existencias.
    """

    class Estado(models.TextChoices):
        BORRADOR = "BORRADOR", "Borrador"
        RECIBIDA = "RECIBIDA", "Recibida"
        ANULADA = "ANULADA", "Anulada"

    proveedor = models.ForeignKey(
        Proveedor,
        verbose_name="proveedor",
        on_delete=models.PROTECT,
        related_name="compras",
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="registrado por",
        on_delete=models.PROTECT,
        related_name="compras_registradas",
    )
    numero_factura = models.CharField("número de factura", max_length=50, blank=True)
    fecha_compra = models.DateField("fecha de compra", default=timezone.localdate)
    fecha_recepcion = models.DateField(
        "fecha de recepción", null=True, blank=True
    )
    estado = models.CharField(
        "estado",
        max_length=10,
        choices=Estado.choices,
        default=Estado.BORRADOR,
    )
    subtotal = models.DecimalField(
        "subtotal",
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    impuesto = models.DecimalField(
        "impuesto",
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    total = models.DecimalField(
        "total",
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    observaciones = models.TextField("observaciones", blank=True)
    creado_en = models.DateTimeField("fecha de registro", auto_now_add=True)
    actualizado_en = models.DateTimeField("última actualización", auto_now=True)

    class Meta:
        verbose_name = "compra"
        verbose_name_plural = "compras"
        ordering = ("-fecha_compra", "-pk")
        indexes = (
            models.Index(fields=("fecha_compra",), name="compras_compra_fecha_idx"),
            models.Index(fields=("estado",), name="compras_compra_estado_idx"),
        )
        constraints = (
            models.CheckConstraint(
                condition=Q(subtotal__gte=0),
                name="compras_compra_subtotal_no_negativo",
            ),
            models.CheckConstraint(
                condition=Q(impuesto__gte=0),
                name="compras_compra_impuesto_no_negativo",
            ),
            models.CheckConstraint(
                condition=Q(total__gte=0),
                name="compras_compra_total_no_negativo",
            ),
        )

    @property
    def numero(self) -> str:
        """Número visible y estable de la compra."""
        if not self.pk:
            return "Sin número"
        return f"C-{self.pk:06d}"

    @property
    def cantidad_productos(self) -> int:
        """Cantidad total de unidades compradas."""
        if not self.pk:
            return 0
        return sum(detalle.cantidad for detalle in self.detalles.all())

    def clean(self):
        """Valida la coherencia de totales, fechas y estado."""
        super().clean()
        self.numero_factura = " ".join((self.numero_factura or "").split())
        self.observaciones = (self.observaciones or "").strip()

        if self.estado == self.Estado.RECIBIDA and not self.fecha_recepcion:
            raise ValidationError(
                {
                    "fecha_recepcion": (
                        "Registra la fecha de recepción de la compra."
                    )
                }
            )
        if self.estado != self.Estado.RECIBIDA and self.fecha_recepcion:
            raise ValidationError(
                {
                    "fecha_recepcion": (
                        "Solo una compra recibida puede tener fecha de "
                        "recepción."
                    )
                }
            )

        # Los totales se recalculan en ``apps.compras.services`` a partir de las
        # líneas; no se validan aquí para no rechazar el formulario, que no
        # envía subtotal ni total.

    def save(self, *args, **kwargs):
        self.numero_factura = " ".join((self.numero_factura or "").split())
        self.observaciones = (self.observaciones or "").strip()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.numero} — {self.proveedor}"


class DetalleCompra(models.Model):
    """Línea de producto incluida en una compra."""

    compra = models.ForeignKey(
        Compra,
        verbose_name="compra",
        on_delete=models.CASCADE,
        related_name="detalles",
    )
    producto = models.ForeignKey(
        "catalogo.Producto",
        verbose_name="producto",
        on_delete=models.PROTECT,
        related_name="detalles_compra",
    )
    lote = models.ForeignKey(
        "inventario.Lote",
        verbose_name="lote",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="detalles_compra",
    )
    cantidad = models.PositiveIntegerField(
        "cantidad",
        validators=[MinValueValidator(1)],
    )
    costo_unitario = models.DecimalField(
        "costo unitario",
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    subtotal = models.DecimalField(
        "subtotal",
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )

    class Meta:
        verbose_name = "detalle de compra"
        verbose_name_plural = "detalles de compra"
        ordering = ("pk",)
        constraints = (
            models.CheckConstraint(
                condition=Q(cantidad__gt=0),
                name="compras_detalle_cantidad_positiva",
            ),
            models.CheckConstraint(
                condition=Q(costo_unitario__gte=0),
                name="compras_detalle_costo_no_negativo",
            ),
            models.CheckConstraint(
                condition=Q(subtotal__gte=0),
                name="compras_detalle_subtotal_no_negativo",
            ),
        )

    def clean(self):
        """Calcula el subtotal y valida el lote asociado."""
        super().clean()

        if self.cantidad is not None and self.costo_unitario is not None:
            self.subtotal = self.costo_unitario * self.cantidad

        if self.lote_id and self.producto_id:
            if self.lote.producto_id != self.producto_id:
                raise ValidationError(
                    {
                        "lote": (
                            "El lote debe pertenecer al producto seleccionado."
                        )
                    }
                )
            if not self.lote.activo:
                raise ValidationError(
                    {"lote": "El lote seleccionado no está activo."}
                )

    def save(self, *args, **kwargs):
        if self.cantidad is not None and self.costo_unitario is not None:
            self.subtotal = self.costo_unitario * self.cantidad
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.producto} x {self.cantidad}"
