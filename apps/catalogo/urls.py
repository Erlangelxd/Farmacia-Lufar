from django.urls import path

from . import views

app_name = "catalogo"

urlpatterns = [
    path("", views.ProductoListView.as_view(), name="index"),
    path(
        "productos/nuevo/",
        views.ProductoCreateView.as_view(),
        name="producto_crear",
    ),
    path(
        "productos/<int:pk>/editar/",
        views.ProductoUpdateView.as_view(),
        name="producto_editar",
    ),
    path(
        "productos/<int:pk>/estado/",
        views.ProductoToggleActiveView.as_view(),
        name="producto_estado",
    ),
    path(
        "categorias/",
        views.CategoriaListView.as_view(),
        name="categorias",
    ),
    path(
        "categorias/nueva/",
        views.CategoriaCreateView.as_view(),
        name="categoria_crear",
    ),
    path(
        "categorias/<int:pk>/editar/",
        views.CategoriaUpdateView.as_view(),
        name="categoria_editar",
    ),
    path(
        "categorias/<int:pk>/estado/",
        views.CategoriaToggleActiveView.as_view(),
        name="categoria_estado",
    ),
]
