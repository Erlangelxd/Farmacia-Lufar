"""Mixins de autorización compartidos entre las aplicaciones."""

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin


class RoleRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Exige autenticación y pertenencia a alguno de los grupos permitidos.

    Los superusuarios siempre tienen acceso. Un usuario autenticado sin el rol
    requerido recibe una respuesta 403; un visitante anónimo es redirigido al
    inicio de sesión.
    """

    allowed_groups: tuple[str, ...] = ()

    def test_func(self) -> bool:
        user = self.request.user
        if not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        return bool(self.allowed_groups) and user.groups.filter(
            name__in=self.allowed_groups
        ).exists()
