"""Vistas compartidas y dashboard del sistema."""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
from django.views.generic import TemplateView

from apps.accounts.constants import ADMIN_GROUP, SELLER_GROUP
from apps.accounts.permissions import is_administrator

from .mixins import RoleRequiredMixin


class DashboardView(LoginRequiredMixin, TemplateView):
    """Panel general con indicadores provisionales de la etapa inicial."""

    template_name = "core/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["today"] = timezone.localdate()
        can_view_stock = is_administrator(self.request.user)
        context["can_view_stock"] = can_view_stock

        cards = [
            {
                "label": "Productos registrados",
                "value": "128",
                "detail": "Catálogo",
                "tone": "green",
            },
            {
                "label": "Ventas del día",
                "value": "34",
                "detail": "Operaciones",
                "tone": "amber",
            },
        ]
        if can_view_stock:
            cards[1:1] = [
                {
                    "label": "Unidades en inventario",
                    "value": "1.240",
                    "detail": "Existencias",
                    "tone": "teal",
                },
            ]
            cards.append(
                {
                    "label": "Compras del mes",
                    "value": "12",
                    "detail": "Abastecimiento",
                    "tone": "blue",
                }
            )
        context["dashboard_cards"] = cards
        return context


class ModulePlaceholderView(RoleRequiredMixin, TemplateView):
    """Base reutilizable para las páginas iniciales de cada módulo.

    Cada app define su título, descripción, alcance y los roles autorizados.
    Cuando se implemente la lógica real, sus vistas podrán dejar de heredar de
    esta clase.
    """

    template_name = "core/placeholder.html"
    allowed_groups = (ADMIN_GROUP, SELLER_GROUP)
    module_title = "Módulo"
    module_code = "MD"
    module_description = ""
    module_scope: tuple[str, ...] = ()
    module_note = (
        "La lógica de este módulo se implementará en la siguiente etapa."
    )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "module_title": self.module_title,
                "module_code": self.module_code,
                "module_description": self.module_description,
                "module_scope": self.module_scope,
                "module_note": self.module_note,
            }
        )
        return context
