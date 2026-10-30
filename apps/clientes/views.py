"""Vistas del módulo de clientes."""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.urls import reverse
from django.views.generic import CreateView, DetailView, ListView

from .forms import ClienteForm
from .models import Cliente


class ClienteListView(LoginRequiredMixin, ListView):
    """Listado de clientes con búsqueda, filtro por estado y paginación."""

    model = Cliente
    template_name = "clientes/cliente_list.html"
    context_object_name = "clientes"
    paginate_by = 20

    def get_queryset(self):
        queryset = super().get_queryset()
        busqueda = self.request.GET.get("q", "").strip()
        estado = self.request.GET.get("estado", "").strip()

        if busqueda:
            queryset = queryset.filter(
                Q(nombre__icontains=busqueda)
                | Q(numero_documento__icontains=busqueda)
                | Q(telefono__icontains=busqueda)
            )

        if estado == "activo":
            queryset = queryset.filter(activo=True)
        elif estado == "inactivo":
            queryset = queryset.filter(activo=False)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["q"] = self.request.GET.get("q", "").strip()
        context["estado"] = self.request.GET.get("estado", "").strip()
        context["total_clientes"] = Cliente.objects.count()
        context["total_activos"] = Cliente.objects.filter(activo=True).count()
        context["total_inactivos"] = Cliente.objects.filter(activo=False).count()

        filtros = self.request.GET.copy()
        filtros.pop("page", None)
        context["querystring"] = filtros.urlencode()

        return context


class ClienteCreateView(LoginRequiredMixin, CreateView):
    """Registro de un cliente nuevo."""

    model = Cliente
    form_class = ClienteForm
    template_name = "clientes/cliente_form.html"

    def form_valid(self, form):
        form.instance.creado_por = self.request.user
        response = super().form_valid(form)
        messages.success(
            self.request,
            f"El cliente {self.object.nombre} se registró correctamente.",
        )
        return response

    def get_success_url(self):
        return reverse("clientes:detalle", kwargs={"pk": self.object.pk})


class ClienteDetailView(LoginRequiredMixin, DetailView):
    """Ficha de consulta de un cliente."""

    model = Cliente
    template_name = "clientes/cliente_detail.html"
    context_object_name = "cliente"

    def get_queryset(self):
        return super().get_queryset().select_related("creado_por")
