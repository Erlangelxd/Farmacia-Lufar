"""Registro de los modelos de compras en el admin.

Las compras recibidas o anuladas son de solo lectura y los registros no se
eliminan desde el admin: el historial de abastecimiento debe conservarse. Los
totales se recalculan a partir de las líneas después de guardar.
"""

from decimal import Decimal

from django.contrib import admin
from django.db.models import Sum

from .models import Compra, DetalleCompra, Proveedor


@admin.register(Proveedor)
class ProveedorAdmin(admin.ModelAdmin):
    list_display = ("nombre", "nit", "telefono", "activo")
    list_filter = ("activo",)
    search_fields = ("nombre", "nit", "contacto")
    readonly_fields = ("creado_en", "actualizado_en")
    list_per_page = 25

    def has_delete_permission(self, request, obj=None):
        return False


class DetalleCompraInline(admin.TabularInline):
    model = DetalleCompra
    extra = 0
    raw_id_fields = ("producto", "lote")
    fields = (
        "producto",
        "lote",
        "cantidad",
        "costo_unitario",
        "subtotal",
    )
    readonly_fields = ("subtotal",)

    def _es_editable(self, obj) -> bool:
        return obj is None or obj.estado == Compra.Estado.BORRADOR

    def has_add_permission(self, request, obj=None):
        if not self._es_editable(obj):
            return False
        return super().has_add_permission(request, obj)

    def has_change_permission(self, request, obj=None):
        if not self._es_editable(obj):
            return False
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        if not self._es_editable(obj):
            return False
        return super().has_delete_permission(request, obj)


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
    readonly_fields = (
        "estado",
        "subtotal",
        "total",
        "creado_en",
        "actualizado_en",
    )
    inlines = (DetalleCompraInline,)
    list_per_page = 25

    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))
        if obj is not None and obj.estado != Compra.Estado.BORRADOR:
            readonly = [field.name for field in obj._meta.fields]
        return readonly

    def has_delete_permission(self, request, obj=None):
        return False

    def save_related(self, request, form, formsets, change):
        """Recalcula subtotal y total después de guardar las líneas."""
        super().save_related(request, form, formsets, change)
        compra = form.instance
        subtotal = compra.detalles.aggregate(total=Sum("subtotal"))["total"]
        compra.subtotal = subtotal or Decimal("0.00")
        compra.total = compra.subtotal + compra.impuesto
        compra.save(update_fields=["subtotal", "total", "actualizado_en"])


@admin.register(DetalleCompra)
class DetalleCompraAdmin(admin.ModelAdmin):
    list_display = (
        "compra",
        "producto",
        "cantidad",
        "costo_unitario",
        "subtotal",
    )
    list_filter = ("compra__estado",)
    search_fields = ("producto__nombre", "compra__numero_factura")
    raw_id_fields = ("compra", "producto", "lote")
    readonly_fields = (
        "compra",
        "producto",
        "lote",
        "cantidad",
        "costo_unitario",
        "subtotal",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
