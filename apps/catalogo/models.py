"""Modelos del catálogo de productos."""

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q


def categoria_predeterminada():
    """Devuelve la categoría ``General`` usada por los productos sin categoría.

    La fila se crea en la migración de datos ``catalogo.0003_categoria_general``.
    Se usa ``get_or_create`` para que la migración que agrega la clave foránea
    también funcione en bases con productos ya cargados.
    """
    categoria, _ = Categoria.objects.get_or_create(
        nombre="General",
        defaults={"descripcion": "Categoría asignada por defecto."},
    )
    return categoria.pk


class Categoria(models.Model):
    """Clasificación general de los productos de la farmacia."""

    nombre = models.CharField("nombre", max_length=80, unique=True)
    descripcion = models.TextField("descripción", blank=True)
    activo = models.BooleanField("categoría activa", default=True)
    creado_en = models.DateTimeField("fecha de registro", auto_now_add=True)
    actualizado_en = models.DateTimeField("última actualización", auto_now=True)

    class Meta:
        verbose_name = "categoría"
        verbose_name_plural = "categorías"
        ordering = ("nombre", "pk")

    def __str__(self) -> str:
        return self.nombre

    def save(self, *args, **kwargs):
        self.nombre = " ".join((self.nombre or "").split())
        super().save(*args, **kwargs)


class Laboratorio(models.Model):
    """Laboratorio fabricante de un producto."""

    nombre = models.CharField("nombre", max_length=120, unique=True)
    pais = models.CharField("país", max_length=80, blank=True)
    activo = models.BooleanField("laboratorio activo", default=True)
    creado_en = models.DateTimeField("fecha de registro", auto_now_add=True)
    actualizado_en = models.DateTimeField("última actualización", auto_now=True)

    class Meta:
        verbose_name = "laboratorio"
        verbose_name_plural = "laboratorios"
        ordering = ("nombre", "pk")

    def __str__(self) -> str:
        return self.nombre

    def save(self, *args, **kwargs):
        self.nombre = " ".join((self.nombre or "").split())
        super().save(*args, **kwargs)


class FormaFarmaceutica(models.Model):
    """Forma de presentación del medicamento (tableta, jarabe, etc.)."""

    nombre = models.CharField("nombre", max_length=80, unique=True)
    creado_en = models.DateTimeField("fecha de registro", auto_now_add=True)
    actualizado_en = models.DateTimeField("última actualización", auto_now=True)

    class Meta:
        verbose_name = "forma farmacéutica"
        verbose_name_plural = "formas farmacéuticas"
        ordering = ("nombre", "pk")

    def __str__(self) -> str:
        return self.nombre

    def save(self, *args, **kwargs):
        self.nombre = " ".join((self.nombre or "").split())
        super().save(*args, **kwargs)


class Presentacion(models.Model):
    """Presentación comercial del producto (caja, frasco, ampolla, etc.)."""

    nombre = models.CharField("nombre", max_length=80, unique=True)
    creado_en = models.DateTimeField("fecha de registro", auto_now_add=True)
    actualizado_en = models.DateTimeField("última actualización", auto_now=True)

    class Meta:
        verbose_name = "presentación"
        verbose_name_plural = "presentaciones"
        ordering = ("nombre", "pk")

    def __str__(self) -> str:
        return self.nombre

    def save(self, *args, **kwargs):
        self.nombre = " ".join((self.nombre or "").split())
        super().save(*args, **kwargs)


class Producto(models.Model):
    """Producto que la farmacia comercializa.

    El stock no se guarda aquí: se controla por lote en la app ``inventario``.
    ``stock_minimo`` solo define el umbral para las alertas de reposición.
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
    descripcion = models.TextField("descripción", blank=True)
    principio_activo = models.CharField(
        "principio activo",
        max_length=150,
        blank=True,
    )
    categoria = models.ForeignKey(
        Categoria,
        verbose_name="categoría",
        on_delete=models.PROTECT,
        related_name="productos",
        default=categoria_predeterminada,
    )
    laboratorio = models.ForeignKey(
        Laboratorio,
        verbose_name="laboratorio",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="productos",
    )
    forma_farmaceutica = models.ForeignKey(
        FormaFarmaceutica,
        verbose_name="forma farmacéutica",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="productos",
    )
    presentacion = models.ForeignKey(
        Presentacion,
        verbose_name="presentación",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="productos",
    )
    concentracion = models.CharField(
        "concentración",
        max_length=80,
        blank=True,
    )
    unidad_medida = models.CharField(
        "unidad de medida",
        max_length=30,
        default="UNIDAD",
    )
    precio_venta = models.DecimalField(
        "precio de venta",
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    stock_minimo = models.PositiveIntegerField(
        "stock mínimo",
        default=0,
        validators=[MinValueValidator(0)],
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
        indexes = (
            models.Index(fields=("nombre",), name="catalogo_producto_nombre_idx"),
        )
        constraints = (
            models.CheckConstraint(
                condition=Q(precio_venta__gte=0),
                name="catalogo_producto_precio_no_negativo",
            ),
            models.CheckConstraint(
                condition=Q(stock_minimo__gte=0),
                name="catalogo_producto_stock_minimo_no_negativo",
            ),
        )

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
