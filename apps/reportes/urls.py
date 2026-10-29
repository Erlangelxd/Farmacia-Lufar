from django.urls import path

from . import views

app_name = "reportes"

urlpatterns = [
    path("", views.ReportesIndexView.as_view(), name="index"),
]
