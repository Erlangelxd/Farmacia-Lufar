"""Vistas compartidas y dashboard del sistema."""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum
from django.utils import timezone
from django.views.generic import TemplateView

from apps.accounts.constants import ADMIN_GROUP, SELLER_GROUP
from apps.accounts.permissions import is_administrator
from apps.catalogo.models import Producto
from apps.compras.models import Compra
from apps.inventario.models import Lote
from apps.inventario.selectors import productos_con_stock_bajo
from apps.ventas.models import Venta

from .mixins import RoleRequiredMixin


class DashboardView(LoginRequiredMixin, TemplateView):
    """Panel general con indicadores operativos de los módulos."""

    template_name = "core/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.localdate()
        month_start = today.replace(day=1)
        context["today"] = today
        can_view_stock = is_administrator(self.request.user)
        context["can_view_stock"] = can_view_stock

        products = Producto.objects.filter(activo=True)
        sales_today = Venta.objects.filter(creado_en__date=today)
        sales_month = Venta.objects.filter(creado_en__date__gte=month_start)
        month_revenue = sales_month.aggregate(total=Sum("total"))["total"] or 0
        cards = [
            {"label": "Productos activos", "value": products.count(), "detail": "Catálogo", "tone": "green"},
            {"label": "Ventas de hoy", "value": sales_today.count(), "detail": "Operaciones", "tone": "amber"},
            {"label": "Ingresos del mes", "value": f"Bs {month_revenue:.2f}", "detail": "Ventas registradas", "tone": "blue"},
        ]
        if can_view_stock:
            stock_total = (
                Lote.objects.filter(activo=True).aggregate(
                    total=Sum("stock_actual")
                )["total"]
                or 0
            )
            purchases_month = Compra.objects.filter(
                fecha_compra__gte=month_start
            ).exclude(estado=Compra.Estado.ANULADA)
            cards.extend(
                [
                    {
                        "label": "Unidades en inventario",
                        "value": stock_total,
                        "detail": "Lotes activos",
                        "tone": "teal",
                    },
                    {
                        "label": "Compras del mes",
                        "value": purchases_month.count(),
                        "detail": "No anuladas",
                        "tone": "blue",
                    },
                    {
                        "label": "Productos con stock bajo",
                        "value": productos_con_stock_bajo().count(),
                        "detail": "Requieren reposición",
                        "tone": "amber",
                    },
                ]
            )
        context["dashboard_cards"] = cards
        context["recent_sales"] = (
            Venta.objects.select_related("cliente", "vendedor")
            .order_by("-creado_en", "-pk")[:5]
        )
        context["sales_month_count"] = sales_month.count()
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
