from django.urls import path

from . import views

app_name = "clientes"

urlpatterns = [
    path("", views.ClienteListView.as_view(), name="index"),
    path("nuevo/", views.ClienteCreateView.as_view(), name="crear"),
    path("<int:pk>/", views.ClienteDetailView.as_view(), name="detalle"),
]
