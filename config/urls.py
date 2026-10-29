"""Rutas principales del proyecto Farmacia Lufar."""

from django.contrib import admin
from django.urls import include, path

admin.site.site_header = "Administración de Farmacia Lufar"
admin.site.site_title = "Farmacia Lufar"
admin.site.index_title = "Gestión del sistema"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("cuentas/", include("apps.accounts.urls")),
    path("catalogo/", include("apps.catalogo.urls")),
    path("inventario/", include("apps.inventario.urls")),
    path("compras/", include("apps.compras.urls")),
    path("clientes/", include("apps.clientes.urls")),
    path("ventas/", include("apps.ventas.urls")),
    path("reportes/", include("apps.reportes.urls")),
    path("", include("apps.core.urls")),
]
