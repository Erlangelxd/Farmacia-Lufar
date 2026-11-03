"""Registro de los modelos de compras en el admin."""

from django.contrib import admin

from .models import Compra, DetalleCompra, Proveedor


@admin.register(Proveedor)
class ProveedorAdmin(admin.ModelAdmin):
    list_display = ("nombre", "nit", "telefono", "activo")
    list_filter = ("activo",)
    search_fields = ("nombre", "nit", "contacto")
    readonly_fields = ("creado_en", "actualizado_en")
    list_per_page = 25


class DetalleCompraInline(admin.TabularInline):
    model = DetalleCompra
    extra = 0
    raw_id_fields = ("producto", "lote")


@admin.register(Compra)
class CompraAdmin(admin.ModelAdmin):
    list_display = (
        "numero",
        "proveedor",
        "fecha_compra",
        "estado",
        "total",
    )
    list_filter = ("estado", "fecha_compra")
    search_fields = ("numero_factura", "proveedor__nombre")
    readonly_fields = ("creado_en", "actualizado_en")
    inlines = (DetalleCompraInline,)
    list_per_page = 25


@admin.register(DetalleCompra)
class DetalleCompraAdmin(admin.ModelAdmin):
    list_display = ("compra", "producto", "lote", "cantidad", "costo_unitario")
    raw_id_fields = ("compra", "producto", "lote")
    list_per_page = 25
