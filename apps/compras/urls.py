"""Rutas del módulo de compras."""

from django.urls import path

from . import views

app_name = "compras"

urlpatterns = [
    path("", views.ComprasIndexView.as_view(), name="index"),
    path(
        "proveedores/",
        views.ProveedorListView.as_view(),
        name="proveedores",
    ),
    path(
        "proveedores/nuevo/",
        views.ProveedorCreateView.as_view(),
        name="proveedor_crear",
    ),
    path(
        "proveedores/<int:pk>/editar/",
        views.ProveedorUpdateView.as_view(),
        name="proveedor_editar",
    ),
    path(
        "proveedores/<int:pk>/estado/",
        views.ProveedorToggleActiveView.as_view(),
        name="proveedor_toggle",
    ),
    path("nueva/", views.CompraCreateView.as_view(), name="compra_crear"),
    path(
        "<int:pk>/editar/",
        views.CompraUpdateView.as_view(),
        name="compra_editar",
    ),
    path(
        "<int:pk>/recibir/",
        views.CompraRecepcionView.as_view(),
        name="compra_recepcion",
    ),
    path(
        "<int:pk>/anular/",
        views.CompraAnularView.as_view(),
        name="compra_anular",
    ),
    path("<int:pk>/", views.CompraDetailView.as_view(), name="compra_detalle"),
]
