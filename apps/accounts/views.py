"""Vistas de autenticación, perfil y administración de cuentas."""

from collections import Counter

from django.contrib import messages
from django.contrib.auth import get_user_model, views as auth_views
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import CreateView, TemplateView, UpdateView

from apps.core.mixins import RoleRequiredMixin

from .constants import ADMIN_GROUP, DEFAULT_GROUPS
from .forms import LoginForm, UserCreateForm, UserUpdateForm
from .permissions import MODULE_ACCESS, is_administrator

User = get_user_model()


def _otros_administradores_activos(user):
    """Cuentas activas que podrían administrar el sistema sin ``user``."""
    return (
        User.objects.filter(is_active=True)
        .filter(Q(is_superuser=True) | Q(groups__name=ADMIN_GROUP))
        .exclude(pk=user.pk)
        .distinct()
    )


def _es_ultimo_administrador(user) -> bool:
    """Indica si ``user`` es el último administrador activo del sistema."""
    if not user.is_active:
        return False
    es_admin = user.is_superuser or user.groups.filter(
        name=ADMIN_GROUP
    ).exists()
    if not es_admin:
        return False
    return not _otros_administradores_activos(user).exists()


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
        context["can_manage_users"] = is_administrator(user)
        context["is_admin_role"] = is_administrator(user)
        context["module_access"] = MODULE_ACCESS
        context["permissions_count"] = len(user.get_all_permissions())
        return context


class UserManagementView(RoleRequiredMixin, TemplateView):
    """Listado y administración de usuarios, roles y permisos."""

    template_name = "accounts/user_management.html"
    allowed_groups = (ADMIN_GROUP,)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        busqueda = self.request.GET.get("q", "").strip()
        rol = self.request.GET.get("rol", "").strip()
        estado = self.request.GET.get("estado", "").strip()

        users = User.objects.prefetch_related(
            "groups", "groups__permissions"
        ).order_by("username")

        if busqueda:
            users = users.filter(
                Q(username__icontains=busqueda)
                | Q(first_name__icontains=busqueda)
                | Q(last_name__icontains=busqueda)
                | Q(email__icontains=busqueda)
            )

        if rol in DEFAULT_GROUPS:
            users = users.filter(groups__name=rol)
        elif rol == "sin_rol":
            users = users.filter(groups__isnull=True)

        if estado == "activos":
            users = users.filter(is_active=True)
        elif estado == "inactivos":
            users = users.filter(is_active=False)

        groups = list(
            Group.objects.filter(name__in=DEFAULT_GROUPS)
            .annotate(num_permissions=Count("permissions"))
            .prefetch_related("permissions__content_type")
            .order_by("name")
        )

        # Resumen legible de los permisos de cada rol, agrupado por app.
        group_cards = []
        for group in groups:
            por_app = Counter(
                permiso.content_type.app_label
                for permiso in group.permissions.all()
            )
            group_cards.append(
                {
                    "group": group,
                    "total": sum(por_app.values()),
                    "apps": sorted(por_app.items()),
                }
            )

        context.update(
            {
                "users": users.distinct(),
                "groups": groups,
                "group_cards": group_cards,
                "module_access": MODULE_ACCESS,
                "total_usuarios": User.objects.count(),
                "total_activos": User.objects.filter(is_active=True).count(),
                "total_inactivos": User.objects.filter(
                    is_active=False
                ).count(),
                "total_administradores": User.objects.filter(
                    Q(is_superuser=True) | Q(groups__name=ADMIN_GROUP),
                    is_active=True,
                )
                .distinct()
                .count(),
                "roles": DEFAULT_GROUPS,
                "q": busqueda,
                "rol": rol,
                "estado": estado,
            }
        )
        return context


class UserCreateView(RoleRequiredMixin, CreateView):
    """Alta de una cuenta nueva desde la interfaz."""

    model = User
    form_class = UserCreateForm
    template_name = "accounts/user_form.html"
    allowed_groups = (ADMIN_GROUP,)

    def get_success_url(self):
        return reverse("accounts:usuarios")

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request,
            f"El usuario {self.object.username} se creó correctamente.",
        )
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "form_title": "Nuevo usuario",
                "form_subtitle": (
                    "Crea la cuenta, asigna un rol y define su contraseña "
                    "inicial."
                ),
                "submit_label": "Crear usuario",
            }
        )
        return context


class UserUpdateView(RoleRequiredMixin, UpdateView):
    """Edición de datos, rol, estado y contraseña de una cuenta."""

    model = User
    form_class = UserUpdateForm
    template_name = "accounts/user_form.html"
    allowed_groups = (ADMIN_GROUP,)

    def get_queryset(self):
        users = User.objects.prefetch_related("groups")
        if not self.request.user.is_superuser:
            users = users.exclude(is_superuser=True)
        return users

    def get_success_url(self):
        return reverse("accounts:usuarios")

    def form_valid(self, form):
        objetivo = self.object
        nuevo_rol = form.cleaned_data["role"]
        activo = form.cleaned_data["is_active"]

        if objetivo == self.request.user:
            if not activo:
                form.add_error(
                    "is_active",
                    "No puedes desactivar tu propia cuenta.",
                )
                return self.form_invalid(form)
            if nuevo_rol != ADMIN_GROUP:
                form.add_error(
                    "role",
                    "No puedes quitarte el rol Administrador.",
                )
                return self.form_invalid(form)

        if _es_ultimo_administrador(objetivo) and (
            not activo or nuevo_rol != ADMIN_GROUP
        ):
            form.add_error(
                None,
                "Debe existir al menos un administrador activo.",
            )
            return self.form_invalid(form)

        response = super().form_valid(form)
        messages.success(
            self.request,
            f"El usuario {self.object.username} se actualizó correctamente.",
        )
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "form_title": f"Editar {self.object.username}",
                "form_subtitle": (
                    "Actualiza los datos, el rol o la contraseña de la "
                    "cuenta."
                ),
                "submit_label": "Guardar cambios",
                "es_superusuario": self.object.is_superuser,
            }
        )
        return context


class UserToggleActiveView(RoleRequiredMixin, View):
    """Activa o desactiva una cuenta mediante POST."""

    allowed_groups = (ADMIN_GROUP,)

    def post(self, request, pk):
        objetivo = get_object_or_404(User, pk=pk)

        if objetivo.is_superuser and not request.user.is_superuser:
            raise PermissionDenied

        if objetivo == request.user:
            messages.error(
                request,
                "No puedes desactivar tu propia cuenta.",
            )
            return redirect("accounts:usuarios")

        if objetivo.is_active and _es_ultimo_administrador(objetivo):
            messages.error(
                request,
                "Debe existir al menos un administrador activo.",
            )
            return redirect("accounts:usuarios")

        objetivo.is_active = not objetivo.is_active
        objetivo.save(update_fields=["is_active"])
        estado = "activada" if objetivo.is_active else "desactivada"
        messages.success(
            request,
            f"La cuenta {objetivo.username} fue {estado}.",
        )
        return redirect("accounts:usuarios")
