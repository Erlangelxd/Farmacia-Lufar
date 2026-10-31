"""Registro de modelos de ventas en el admin.

Las ventas se consultan en modo de solo lectura. Su creación y sus cálculos
pasan por el servicio transaccional del módulo.
"""

from django.contrib import admin

from .models import DetalleVenta, Venta


class DetalleVentaInline(admin.TabularInline):
    """Detalle de solo lectura de una venta."""

    model = DetalleVenta
    extra = 0
    can_delete = False
    readonly_fields = (
        "producto",
        "codigo_producto",
        "nombre_producto",
        "cantidad",
        "precio_unitario",
        "subtotal",
    )

    @admin.display(description="Subtotal")
    def subtotal(self, obj):
        return obj.subtotal

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(Venta)
class VentaAdmin(admin.ModelAdmin):
    """Consulta de ventas registradas desde la interfaz del sistema."""

    list_display = (
        "numero",
        "cliente",
        "vendedor",
        "total",
        "metodo_pago",
        "creado_en",
    )
    list_filter = ("metodo_pago", "creado_en")
    search_fields = (
        "cliente__nombre",
        "cliente__numero_documento",
        "vendedor__username",
    )
    readonly_fields = (
        "numero",
        "cliente",
        "vendedor",
        "metodo_pago",
        "monto_recibido",
        "total",
        "cambio",
        "creado_en",
    )
    inlines = (DetalleVentaInline,)
    date_hierarchy = "creado_en"
    list_select_related = ("cliente", "vendedor")
    list_per_page = 25
    ordering = ("-creado_en", "-pk")

    @admin.display(description="Número")
    def numero(self, obj):
        return obj.numero

    @admin.display(description="Cambio")
    def cambio(self, obj):
        return obj.cambio

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
