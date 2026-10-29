from django.urls import path

from . import views

app_name = "compras"

urlpatterns = [
    path("", views.ComprasIndexView.as_view(), name="index"),
]
