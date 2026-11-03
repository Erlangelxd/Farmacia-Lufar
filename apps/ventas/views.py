"""Vistas del módulo de ventas."""

from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.db.models import Q, Sum
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views import View
from django.views.generic import DetailView, ListView

from apps.catalogo.models import Producto
from apps.clientes.models import Cliente

from .forms import DetalleVentaFormSet, VentaForm
from .models import Venta
from .services import registrar_venta

class VentaListView(LoginRequiredMixin, ListView):
    """Listado de ventas con búsqueda, filtro por cliente y paginación."""

    model = Venta
    template_name = "ventas/venta_list.html"
    context_object_name = "ventas"
    paginate_by = 20

    def get_queryset(self):
        queryset = (
            super()
            .get_queryset()
            .select_related("cliente", "vendedor")
            .prefetch_related("detalles")
        )
        busqueda = self.request.GET.get("q", "").strip()
        cliente_id = self.request.GET.get("cliente", "").strip()

        if busqueda:
            filtro = (
                Q(cliente__nombre__icontains=busqueda)
                | Q(cliente__numero_documento__icontains=busqueda)
                | Q(detalles__nombre_producto__icontains=busqueda)
                | Q(detalles__codigo_producto__icontains=busqueda)
            )
            numero = busqueda.upper()
            if numero.startswith("V-"):
                numero = numero[2:]
            if numero.isdigit() and len(numero) <= 7:
                filtro |= Q(pk=int(numero))
            queryset = queryset.filter(filtro).distinct()

        if cliente_id.isdigit():
            queryset = queryset.filter(cliente_id=int(cliente_id))

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        hoy = timezone.localdate()
        ventas_hoy = Venta.objects.filter(creado_en__date=hoy)
        context["q"] = self.request.GET.get("q", "").strip()
        context["cliente_id"] = self.request.GET.get("cliente", "").strip()
        context["clientes"] = Cliente.objects.order_by("nombre")
        context["total_ventas"] = Venta.objects.count()
        context["ventas_hoy"] = ventas_hoy.count()
        context["ingresos_hoy"] = (
            ventas_hoy.aggregate(total=Sum("total"))["total"]
            or Decimal("0.00")
        )

        filtros = self.request.GET.copy()
        filtros.pop("page", None)
        context["querystring"] = filtros.urlencode()
        return context


class VentaCreateView(LoginRequiredMixin, View):
    """Registro de una venta con sus líneas de detalle."""

    template_name = "ventas/venta_form.html"

    def get(self, request):
        return self._render(
            request,
            VentaForm(),
            DetalleVentaFormSet(instance=Venta(), prefix="detalles"),
        )

    def post(self, request):
        form = VentaForm(request.POST)
        formset = DetalleVentaFormSet(
            request.POST,
            instance=Venta(),
            prefix="detalles",
        )
        form_valido = form.is_valid()
        formset_valido = formset.is_valid()

        if form_valido and formset_valido:
            lineas = [
                {
                    "producto": detalle_form.cleaned_data["producto"],
                    "cantidad": detalle_form.cleaned_data["cantidad"],
                }
                for detalle_form in formset.forms
                if detalle_form.cleaned_data
                and not detalle_form.cleaned_data.get("DELETE")
                and detalle_form.cleaned_data.get("producto")
            ]
            try:
                venta = registrar_venta(
                    vendedor=request.user,
                    cliente=form.cleaned_data["cliente"],
                    metodo_pago=form.cleaned_data["metodo_pago"],
                    monto_recibido=form.cleaned_data["monto_recibido"],
                    lineas=lineas,
                )
            except ValidationError as error:
                for mensaje in error.messages:
                    form.add_error(None, mensaje)
            else:
                messages.success(
                    request,
                    f"La venta {venta.numero} se registró correctamente.",
                )
                return redirect("ventas:detalle", pk=venta.pk)

        return self._render(request, form, formset)

    def _render(self, request, form, formset):
        return render(
            request,
            self.template_name,
            {
                "form": form,
                "formset": formset,
                "productos_disponibles": Producto.objects.filter(
                    activo=True
                ).exists(),
            },
        )


class VentaDetailView(LoginRequiredMixin, DetailView):
    """Ficha de consulta de una venta."""

    model = Venta
    template_name = "ventas/venta_detail.html"
    context_object_name = "venta"

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related("cliente", "vendedor")
            .prefetch_related("detalles")
        )


class VentaTicketView(VentaDetailView):
    """Ticket imprimible de una venta."""

    template_name = "ventas/ticket.html"
