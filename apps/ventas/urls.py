from django.urls import path

from . import views

app_name = "ventas"

urlpatterns = [
    path("", views.VentaListView.as_view(), name="index"),
    path("nueva/", views.VentaCreateView.as_view(), name="crear"),
    path("<int:pk>/", views.VentaDetailView.as_view(), name="detalle"),
    path("<int:pk>/ticket/", views.VentaTicketView.as_view(), name="ticket"),
]
