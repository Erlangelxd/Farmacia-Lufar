from django.urls import path

from . import views

app_name = "inventario"

urlpatterns = [
    path("", views.InventarioIndexView.as_view(), name="index"),
    path("lotes/", views.LoteListView.as_view(), name="lotes"),
    path(
        "lotes/nuevo/",
        views.LoteCreateView.as_view(),
        name="lote_crear",
    ),
    path(
        "lotes/<int:pk>/editar/",
        views.LoteUpdateView.as_view(),
        name="lote_editar",
    ),
    path(
        "lotes/<int:pk>/estado/",
        views.LoteToggleActiveView.as_view(),
        name="lote_estado",
    ),
    path(
        "movimientos/",
        views.MovimientoListView.as_view(),
        name="movimientos",
    ),
    path(
        "movimientos/nuevo/",
        views.MovimientoCreateView.as_view(),
        name="movimiento_crear",
    ),
]
