"""Registro del modelo de catálogo en el admin de Django."""

from django.contrib import admin

from .models import Producto


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    """Administración básica de los productos disponibles para venta."""

    list_display = (
        "codigo",
        "nombre",
        "precio_venta",
        "activo",
        "actualizado_en",
    )
    list_filter = ("activo",)
    search_fields = ("codigo", "nombre")
    readonly_fields = ("creado_en", "actualizado_en")
    list_per_page = 25
    ordering = ("nombre",)
