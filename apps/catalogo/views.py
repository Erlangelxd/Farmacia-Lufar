"""Vistas del catálogo de productos y categorías."""

from django.contrib import messages
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import CreateView, ListView, UpdateView

from apps.accounts.constants import ADMIN_GROUP, SELLER_GROUP
from apps.accounts.permissions import is_administrator
from apps.core.mixins import RoleRequiredMixin

from .forms import CategoriaForm, ProductoForm
from .models import Categoria, Producto

CATALOG_ROLES = (ADMIN_GROUP, SELLER_GROUP)
ADMIN_ROLES = (ADMIN_GROUP,)


class ProductoListView(RoleRequiredMixin, ListView):
    """Listado de productos con búsqueda, filtros y paginación."""

    allowed_groups = CATALOG_ROLES
    model = Producto
    template_name = "catalogo/producto_list.html"
    context_object_name = "productos"
    paginate_by = 20

    def get_queryset(self):
        queryset = super().get_queryset().select_related(
            "categoria",
            "laboratorio",
        )
        busqueda = self.request.GET.get("q", "").strip()
        categoria = self.request.GET.get("categoria", "").strip()
        estado = self.request.GET.get("estado", "").strip()

        if busqueda:
            queryset = queryset.filter(
                Q(codigo__icontains=busqueda)
                | Q(nombre__icontains=busqueda)
                | Q(principio_activo__icontains=busqueda)
                | Q(categoria__nombre__icontains=busqueda)
            )

        if categoria.isdigit():
            queryset = queryset.filter(categoria_id=categoria)

        if estado == "activo":
            queryset = queryset.filter(activo=True)
        elif estado == "inactivo":
            queryset = queryset.filter(activo=False)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "q": self.request.GET.get("q", "").strip(),
                "categoria": self.request.GET.get("categoria", "").strip(),
                "estado": self.request.GET.get("estado", "").strip(),
                "categorias": Categoria.objects.order_by("nombre"),
                "total_productos": Producto.objects.count(),
                "total_activos": Producto.objects.filter(activo=True).count(),
                "total_inactivos": Producto.objects.filter(
                    activo=False
                ).count(),
                "total_categorias": Categoria.objects.count(),
                "puede_administrar": is_administrator(self.request.user),
            }
        )

        filtros = self.request.GET.copy()
        filtros.pop("page", None)
        context["querystring"] = filtros.urlencode()
        return context


class ProductoCreateView(RoleRequiredMixin, CreateView):
    """Registro de un producto nuevo."""

    allowed_groups = ADMIN_ROLES
    model = Producto
    form_class = ProductoForm
    template_name = "catalogo/producto_form.html"

    def get_success_url(self):
        return reverse("catalogo:index")

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request,
            f"El producto {self.object.codigo} se registró correctamente.",
        )
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "form_title": "Nuevo producto",
                "form_subtitle": (
                    "Registra los datos del producto. El stock se controla "
                    "por lote en el módulo de inventario."
                ),
                "submit_label": "Guardar producto",
            }
        )
        return context


class ProductoUpdateView(RoleRequiredMixin, UpdateView):
    """Edición de los datos maestros de un producto."""

    allowed_groups = ADMIN_ROLES
    model = Producto
    form_class = ProductoForm
    template_name = "catalogo/producto_form.html"

    def get_success_url(self):
        return reverse("catalogo:index")

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request,
            f"El producto {self.object.codigo} se actualizó correctamente.",
        )
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "form_title": f"Editar {self.object.codigo}",
                "form_subtitle": (
                    "Actualiza los datos maestros del producto. Los cambios "
                    "no modifican las ventas ya registradas."
                ),
                "submit_label": "Guardar cambios",
            }
        )
        return context


class ProductoToggleActiveView(RoleRequiredMixin, View):
    """Activa o desactiva un producto mediante POST."""

    allowed_groups = ADMIN_ROLES

    def post(self, request, pk):
        producto = get_object_or_404(Producto, pk=pk)
        producto.activo = not producto.activo
        producto.save(update_fields=["activo", "actualizado_en"])
        estado = "activado" if producto.activo else "desactivado"
        messages.success(
            request,
            f"El producto {producto.codigo} fue {estado}.",
        )
        return redirect("catalogo:index")


class CategoriaListView(RoleRequiredMixin, ListView):
    """Listado de categorías con sus productos asociados."""

    allowed_groups = CATALOG_ROLES
    model = Categoria
    template_name = "catalogo/categoria_list.html"
    context_object_name = "categorias"
    paginate_by = 20

    def get_queryset(self):
        queryset = (
            super()
            .get_queryset()
            .annotate(
                total_productos=Count("productos"),
                productos_activos=Count(
                    "productos",
                    filter=Q(productos__activo=True),
                ),
            )
        )
        busqueda = self.request.GET.get("q", "").strip()
        estado = self.request.GET.get("estado", "").strip()

        if busqueda:
            queryset = queryset.filter(
                Q(nombre__icontains=busqueda)
                | Q(descripcion__icontains=busqueda)
            )

        if estado == "activo":
            queryset = queryset.filter(activo=True)
        elif estado == "inactivo":
            queryset = queryset.filter(activo=False)

        return queryset.order_by("nombre", "pk")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "q": self.request.GET.get("q", "").strip(),
                "estado": self.request.GET.get("estado", "").strip(),
                "total_categorias": Categoria.objects.count(),
                "total_activas": Categoria.objects.filter(
                    activo=True
                ).count(),
                "total_inactivas": Categoria.objects.filter(
                    activo=False
                ).count(),
                "total_productos": Producto.objects.count(),
                "puede_administrar": is_administrator(self.request.user),
            }
        )

        filtros = self.request.GET.copy()
        filtros.pop("page", None)
        context["querystring"] = filtros.urlencode()
        return context


class CategoriaCreateView(RoleRequiredMixin, CreateView):
    """Registro de una categoría nueva."""

    allowed_groups = ADMIN_ROLES
    model = Categoria
    form_class = CategoriaForm
    template_name = "catalogo/categoria_form.html"

    def get_success_url(self):
        return reverse("catalogo:categorias")

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request,
            f"La categoría {self.object.nombre} se registró correctamente.",
        )
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "form_title": "Nueva categoría",
                "form_subtitle": (
                    "Agrupa productos por tipo para facilitar su búsqueda y "
                    "consulta."
                ),
                "submit_label": "Guardar categoría",
            }
        )
        return context


class CategoriaUpdateView(RoleRequiredMixin, UpdateView):
    """Edición de una categoría existente."""

    allowed_groups = ADMIN_ROLES
    model = Categoria
    form_class = CategoriaForm
    template_name = "catalogo/categoria_form.html"

    def get_success_url(self):
        return reverse("catalogo:categorias")

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request,
            f"La categoría {self.object.nombre} se actualizó correctamente.",
        )
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "form_title": f"Editar {self.object.nombre}",
                "form_subtitle": (
                    "Actualiza el nombre, la descripción o el estado de la "
                    "categoría."
                ),
                "submit_label": "Guardar cambios",
            }
        )
        return context


class CategoriaToggleActiveView(RoleRequiredMixin, View):
    """Activa o desactiva una categoría mediante POST."""

    allowed_groups = ADMIN_ROLES

    def post(self, request, pk):
        categoria = get_object_or_404(Categoria, pk=pk)

        if categoria.activo and categoria.productos.filter(
            activo=True
        ).exists():
            messages.error(
                request,
                (
                    f"No puedes desactivar la categoría {categoria.nombre} "
                    "mientras tenga productos activos."
                ),
            )
            return redirect("catalogo:categorias")

        categoria.activo = not categoria.activo
        categoria.save(update_fields=["activo", "actualizado_en"])
        estado = "activada" if categoria.activo else "desactivada"
        messages.success(
            request,
            f"La categoría {categoria.nombre} fue {estado}.",
        )
        return redirect("catalogo:categorias")
