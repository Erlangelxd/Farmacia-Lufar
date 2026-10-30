"""Registro del modelo de clientes en el admin de Django."""

from django.contrib import admin

from .models import Cliente


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    """Administración básica de clientes."""

    list_display = (
        "nombre",
        "tipo_documento",
        "numero_documento",
        "telefono",
        "activo",
        "creado_en",
    )
    list_filter = ("tipo_documento", "activo")
    search_fields = ("nombre", "numero_documento", "telefono")
    readonly_fields = ("creado_en", "actualizado_en", "creado_por")
    date_hierarchy = "creado_en"
    list_select_related = ("creado_por",)
    list_per_page = 25
    ordering = ("nombre",)

    def save_model(self, request, obj, form, change):
        if not change and not obj.creado_por:
            obj.creado_por = request.user
        super().save_model(request, obj, form, change)
