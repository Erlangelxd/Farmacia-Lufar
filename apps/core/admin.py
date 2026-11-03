"""Registro de la configuración del sistema en el admin."""

from django.contrib import admin

from .models import ConfiguracionSistema


@admin.register(ConfiguracionSistema)
class ConfiguracionSistemaAdmin(admin.ModelAdmin):
    list_display = ("nombre_empresa", "moneda", "actualizado_en")
    readonly_fields = ("actualizado_en",)

    def has_add_permission(self, request):
        return not ConfiguracionSistema.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
