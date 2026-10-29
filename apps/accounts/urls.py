from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("", views.AccountHomeView.as_view(), name="index"),
    path("login/", views.LoginView.as_view(), name="login"),
    path("logout/", views.LogoutView.as_view(), name="logout"),
    path("usuarios/", views.UserManagementView.as_view(), name="usuarios"),
]
