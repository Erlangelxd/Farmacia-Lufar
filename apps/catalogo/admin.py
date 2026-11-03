"""Registro de los modelos de catálogo en el admin de Django."""

from django.contrib import admin

from .models import (
    Categoria,
    FormaFarmaceutica,
    Laboratorio,
    Presentacion,
    Producto,
)


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "activo", "actualizado_en")
    list_filter = ("activo",)
    search_fields = ("nombre",)
    readonly_fields = ("creado_en", "actualizado_en")
    list_per_page = 25


@admin.register(Laboratorio)
class LaboratorioAdmin(admin.ModelAdmin):
    list_display = ("nombre", "pais", "activo")
    list_filter = ("activo",)
    search_fields = ("nombre", "pais")
    readonly_fields = ("creado_en", "actualizado_en")
    list_per_page = 25


@admin.register(FormaFarmaceutica)
class FormaFarmaceuticaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "actualizado_en")
    search_fields = ("nombre",)
    readonly_fields = ("creado_en", "actualizado_en")
    list_per_page = 25


@admin.register(Presentacion)
class PresentacionAdmin(admin.ModelAdmin):
    list_display = ("nombre", "actualizado_en")
    search_fields = ("nombre",)
    readonly_fields = ("creado_en", "actualizado_en")
    list_per_page = 25


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    """Administración de los productos disponibles para venta."""

    list_display = (
        "codigo",
        "nombre",
        "categoria",
        "precio_venta",
        "stock_minimo",
        "activo",
        "actualizado_en",
    )
    list_filter = ("activo", "categoria", "laboratorio")
    search_fields = ("codigo", "nombre", "principio_activo")
    readonly_fields = ("creado_en", "actualizado_en")
    list_per_page = 25
    ordering = ("nombre",)
