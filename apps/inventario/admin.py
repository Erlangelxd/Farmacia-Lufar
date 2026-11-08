"""Registro de los modelos de inventario en el admin."""

from django.contrib import admin

from .models import (
    AjusteCostoInventario,
    AsignacionCostoInventario,
    CapaCosto,
    Lote,
    MovimientoInventario,
)


@admin.register(Lote)
class LoteAdmin(admin.ModelAdmin):
    list_display = (
        "codigo_lote",
        "producto",
        "fecha_vencimiento",
        "stock_actual",
        "activo",
    )
    list_filter = ("activo", "fecha_vencimiento")
    search_fields = ("codigo_lote", "producto__codigo", "producto__nombre")
    readonly_fields = ("stock_actual", "creado_en", "actualizado_en")
    list_per_page = 25

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(MovimientoInventario)
class MovimientoInventarioAdmin(admin.ModelAdmin):
    """Los movimientos son inmutables: solo se consultan desde el admin."""

    list_display = (
        "fecha",
        "lote",
        "tipo",
        "cantidad",
        "stock_resultante",
        "costo_total",
    )
    list_filter = ("tipo", "fecha")
    search_fields = ("lote__codigo_lote", "lote__producto__nombre", "motivo")
    date_hierarchy = "fecha"
    list_per_page = 25

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class CostoInmutableAdmin(admin.ModelAdmin):
    """Las capas y asignaciones de costo solo se consultan en el admin."""

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(CapaCosto)
class CapaCostoAdmin(CostoInmutableAdmin):
    list_display = (
        "lote",
        "cantidad_inicial",
        "cantidad_restante",
        "costo_unitario",
        "creado_en",
    )
    list_filter = ("creado_en",)
    search_fields = ("lote__codigo_lote", "lote__producto__nombre")


@admin.register(AsignacionCostoInventario)
class AsignacionCostoInventarioAdmin(CostoInmutableAdmin):
    list_display = ("movimiento", "capa", "cantidad", "costo_unitario")
    list_filter = ("movimiento__fecha",)
    search_fields = ("capa__lote__codigo_lote", "capa__lote__producto__nombre")


@admin.register(AjusteCostoInventario)
class AjusteCostoInventarioAdmin(CostoInmutableAdmin):
    list_display = ("fecha", "lote", "cantidad", "costo_unitario", "usuario")
    list_filter = ("fecha",)
    search_fields = ("lote__codigo_lote", "lote__producto__nombre", "motivo")
