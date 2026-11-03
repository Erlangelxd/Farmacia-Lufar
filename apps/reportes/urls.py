from django.urls import path

from . import views

app_name = "reportes"

urlpatterns = [
    path("", views.ReportesIndexView.as_view(), name="index"),
    path("ventas/", views.ReporteVentasView.as_view(), name="ventas"),
    path("compras/", views.ReporteComprasView.as_view(), name="compras"),
    path("inventario/", views.ReporteInventarioView.as_view(), name="inventario"),
]
