"""Vistas de autenticación, perfil y administración de cuentas."""

from django.contrib import messages
from django.contrib.auth import get_user_model, views as auth_views
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import Group
from django.urls import reverse_lazy
from django.views.generic import TemplateView

from apps.core.mixins import RoleRequiredMixin

from .constants import ADMIN_GROUP
from .forms import LoginForm


class LoginView(auth_views.LoginView):
    """Inicio de sesión con el formulario y la autenticación de Django."""

    template_name = "registration/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True

    def form_valid(self, form):
        response = super().form_valid(form)
        name = self.request.user.get_full_name() or self.request.user.username
        messages.success(self.request, f"Bienvenido, {name}.")
        return response


class LogoutView(auth_views.LogoutView):
    """Cierre de sesión mediante POST y redirección al login."""

    next_page = reverse_lazy("accounts:login")

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        messages.success(request, "Has cerrado sesión correctamente.")
        return response


class AccountHomeView(LoginRequiredMixin, TemplateView):
    """Resumen de la cuenta autenticada y sus roles."""

    template_name = "accounts/index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context["groups"] = user.groups.all()
        context["can_manage_users"] = (
            user.is_superuser
            or user.groups.filter(name=ADMIN_GROUP).exists()
        )
        return context


class UserManagementView(RoleRequiredMixin, TemplateView):
    """Vista de solo lectura de usuarios y grupos para administradores."""

    template_name = "accounts/user_management.html"
    allowed_groups = (ADMIN_GROUP,)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user_model = get_user_model()
        context["users"] = (
            user_model.objects.prefetch_related("groups").order_by("username")
        )
        context["groups"] = Group.objects.prefetch_related(
            "permissions"
        ).order_by("name")
        return context
