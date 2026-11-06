"""Vistas del módulo de inventario."""

from datetime import timedelta
from decimal import Decimal

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import Count, F, Q, Sum
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, FormView, ListView, UpdateView

from apps.accounts.constants import ADMIN_GROUP
from apps.catalogo.models import Producto
from apps.core.mixins import RoleRequiredMixin

from .forms import LoteForm, MovimientoForm
from .models import Lote, MovimientoInventario
from .selectors import productos_con_stock_bajo, stock_por_producto
from .services import crear_lote, registrar_movimiento

ADMIN_ROLES = (ADMIN_GROUP,)
DIAS_POR_VENCER = 30


def _agregar_errores_al_formulario(form, error: ValidationError) -> None:
    """Vuelca los errores de un servicio de inventario en el formulario."""
    if hasattr(error, "message_dict"):
        for campo, mensajes in error.message_dict.items():
            for mensaje in mensajes:
                form.add_error(campo if campo in form.fields else None, mensaje)
        return

    for mensaje in error.messages:
        form.add_error(None, mensaje)


class InventarioIndexView(RoleRequiredMixin, ListView):
    """Existencias por producto, con alertas de stock bajo y vencimientos."""

    allowed_groups = ADMIN_ROLES
    model = Producto
    template_name = "inventario/index.html"
    context_object_name = "productos"
    paginate_by = 20

    def get_queryset(self):
        queryset = (
            super()
            .get_queryset()
            .select_related("categoria", "laboratorio")
            .annotate(
                stock_total=stock_por_producto(),
                total_lotes=Count(
                    "lotes",
                    filter=Q(lotes__activo=True),
                    distinct=True,
                ),
            )
        )

        busqueda = self.request.GET.get("q", "").strip()
        estado = self.request.GET.get("estado", "activos").strip()
        alerta = self.request.GET.get("alerta", "todas").strip()

        if busqueda:
            queryset = queryset.filter(
                Q(codigo__icontains=busqueda)
                | Q(nombre__icontains=busqueda)
                | Q(principio_activo__icontains=busqueda)
            )

        if estado == "activos":
            queryset = queryset.filter(activo=True)
        elif estado == "inactivos":
            queryset = queryset.filter(activo=False)

        hoy = timezone.localdate()
        limite_vencimiento = hoy + timedelta(days=DIAS_POR_VENCER)

        if alerta == "bajo":
            queryset = queryset.filter(
                activo=True,
                stock_total__lte=F("stock_minimo"),
            )
        elif alerta == "sin_stock":
            queryset = queryset.filter(
                activo=True,
                stock_total=Decimal("0.00"),
            )
        elif alerta == "por_vencer":
            queryset = queryset.filter(
                activo=True,
                pk__in=Lote.objects.filter(
                    activo=True,
                    fecha_vencimiento__gte=hoy,
                    fecha_vencimiento__lte=limite_vencimiento,
                    stock_actual__gt=0,
                ).values("producto_id"),
            )
        elif alerta == "vencido":
            queryset = queryset.filter(
                activo=True,
                pk__in=Lote.objects.filter(
                    activo=True,
                    fecha_vencimiento__lt=hoy,
                    stock_actual__gt=0,
                ).values("producto_id"),
            )

        return queryset.order_by("nombre", "pk")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        hoy = timezone.localdate()
        limite_vencimiento = hoy + timedelta(days=DIAS_POR_VENCER)
        lotes_activos = Lote.objects.filter(activo=True)

        context.update(
            {
                "q": self.request.GET.get("q", "").strip(),
                "estado": self.request.GET.get("estado", "activos").strip(),
                "alerta": self.request.GET.get("alerta", "todas").strip(),
                "total_productos": Producto.objects.count(),
                "total_activos": Producto.objects.filter(activo=True).count(),
                "total_lotes": lotes_activos.count(),
                "stock_unidades": (
                    lotes_activos.aggregate(total=Sum("stock_actual"))["total"]
                    or Decimal("0.00")
                ),
                "total_stock_bajo": productos_con_stock_bajo().count(),
                "total_por_vencer": lotes_activos.filter(
                    fecha_vencimiento__gte=hoy,
                    fecha_vencimiento__lte=limite_vencimiento,
                    stock_actual__gt=0,
                ).count(),
                "total_vencidos": lotes_activos.filter(
                    fecha_vencimiento__lt=hoy,
                    stock_actual__gt=0,
                ).count(),
                "hoy": hoy,
                "dias_por_vencer": DIAS_POR_VENCER,
            }
        )

        filtros = self.request.GET.copy()
        filtros.pop("page", None)
        context["querystring"] = filtros.urlencode()
        return context


class LoteListView(RoleRequiredMixin, ListView):
    """Listado de lotes con búsqueda, estado y filtro de vencimiento."""

    allowed_groups = ADMIN_ROLES
    model = Lote
    template_name = "inventario/lote_list.html"
    context_object_name = "lotes"
    paginate_by = 20

    def get_queryset(self):
        queryset = super().get_queryset().select_related("producto")
        busqueda = self.request.GET.get("q", "").strip()
        estado = self.request.GET.get("estado", "activos").strip()
        vencimiento = self.request.GET.get("vencimiento", "todos").strip()

        if busqueda:
            queryset = queryset.filter(
                Q(codigo_lote__icontains=busqueda)
                | Q(producto__codigo__icontains=busqueda)
                | Q(producto__nombre__icontains=busqueda)
            )

        if estado == "activos":
            queryset = queryset.filter(activo=True)
        elif estado == "inactivos":
            queryset = queryset.filter(activo=False)

        hoy = timezone.localdate()
        limite_vencimiento = hoy + timedelta(days=DIAS_POR_VENCER)

        if vencimiento == "vencidos":
            queryset = queryset.filter(fecha_vencimiento__lt=hoy)
        elif vencimiento == "por_vencer":
            queryset = queryset.filter(
                fecha_vencimiento__gte=hoy,
                fecha_vencimiento__lte=limite_vencimiento,
            )
        elif vencimiento == "sin_vencimiento":
            queryset = queryset.filter(fecha_vencimiento__isnull=True)

        return queryset.order_by(
            "producto__nombre",
            "fecha_vencimiento",
            "pk",
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        hoy = timezone.localdate()
        context.update(
            {
                "q": self.request.GET.get("q", "").strip(),
                "estado": self.request.GET.get("estado", "activos").strip(),
                "vencimiento": self.request.GET.get(
                    "vencimiento", "todos"
                ).strip(),
                "total_lotes": Lote.objects.count(),
                "total_activos": Lote.objects.filter(activo=True).count(),
                "total_inactivos": Lote.objects.filter(activo=False).count(),
                "total_con_stock": Lote.objects.filter(
                    stock_actual__gt=0
                ).count(),
                "hoy": hoy,
                "limite_vencimiento": hoy
                + timedelta(days=DIAS_POR_VENCER),
                "dias_por_vencer": DIAS_POR_VENCER,
            }
        )

        filtros = self.request.GET.copy()
        filtros.pop("page", None)
        context["querystring"] = filtros.urlencode()
        return context


class LoteCreateView(RoleRequiredMixin, CreateView):
    """Alta de un lote con su stock inicial, registrado como movimiento."""

    allowed_groups = ADMIN_ROLES
    model = Lote
    form_class = LoteForm
    template_name = "inventario/lote_form.html"

    def get_success_url(self):
        return reverse("inventario:lotes")

    def form_valid(self, form):
        datos = form.cleaned_data
        try:
            lote = crear_lote(
                producto=datos["producto"],
                codigo_lote=datos["codigo_lote"],
                fecha_fabricacion=datos.get("fecha_fabricacion"),
                fecha_vencimiento=datos.get("fecha_vencimiento"),
                fecha_ingreso=datos.get("fecha_ingreso"),
                stock_inicial=datos.get("stock_inicial") or Decimal("0.00"),
                activo=datos.get("activo", True),
                usuario=self.request.user,
            )
        except ValidationError as error:
            _agregar_errores_al_formulario(form, error)
            return self.form_invalid(form)

        self.object = lote
        messages.success(
            self.request,
            (
                f"El lote {lote.codigo_lote} de {lote.producto.nombre} "
                "se registró correctamente."
            ),
        )
        return redirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "form_title": "Nuevo lote",
                "form_subtitle": (
                    "Registra el lote y su stock inicial. Los cambios "
                    "posteriores se hacen con movimientos de inventario."
                ),
                "submit_label": "Guardar lote",
                "es_creacion": True,
            }
        )
        return context


class LoteUpdateView(RoleRequiredMixin, UpdateView):
    """Edición de los datos del lote sin modificar sus existencias."""

    allowed_groups = ADMIN_ROLES
    model = Lote
    form_class = LoteForm
    template_name = "inventario/lote_form.html"

    def get_success_url(self):
        return reverse("inventario:lotes")

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request,
            f"El lote {self.object.codigo_lote} se actualizó correctamente.",
        )
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "form_title": f"Editar lote {self.object.codigo_lote}",
                "form_subtitle": (
                    "Actualiza los datos del lote. El stock actual solo "
                    "cambia mediante movimientos de inventario."
                ),
                "submit_label": "Guardar cambios",
                "es_creacion": False,
            }
        )
        return context


class LoteToggleActiveView(RoleRequiredMixin, View):
    """Activa o desactiva un lote mediante POST."""

    allowed_groups = ADMIN_ROLES

    def post(self, request, pk):
        lote = get_object_or_404(Lote, pk=pk)
        lote.activo = not lote.activo

        try:
            lote.full_clean()
        except ValidationError as error:
            for mensaje in error.messages:
                messages.error(request, mensaje)
            return redirect("inventario:lotes")

        lote.save(update_fields=["activo", "actualizado_en"])
        estado = "activado" if lote.activo else "desactivado"
        messages.success(
            request,
            f"El lote {lote.codigo_lote} fue {estado}.",
        )
        return redirect("inventario:lotes")


class MovimientoListView(RoleRequiredMixin, ListView):
    """Historial inmutable de movimientos de inventario."""

    allowed_groups = ADMIN_ROLES
    model = MovimientoInventario
    template_name = "inventario/movimiento_list.html"
    context_object_name = "movimientos"
    paginate_by = 25

    def get_queryset(self):
        queryset = super().get_queryset().select_related(
            "lote__producto",
            "usuario",
        )
        busqueda = self.request.GET.get("q", "").strip()
        tipo = self.request.GET.get("tipo", "").strip()

        if busqueda:
            queryset = queryset.filter(
                Q(lote__codigo_lote__icontains=busqueda)
                | Q(lote__producto__codigo__icontains=busqueda)
                | Q(lote__producto__nombre__icontains=busqueda)
                | Q(motivo__icontains=busqueda)
                | Q(usuario__username__icontains=busqueda)
                | Q(usuario__first_name__icontains=busqueda)
                | Q(usuario__last_name__icontains=busqueda)
            )

        tipos_validos = {
            choice[0] for choice in MovimientoInventario.Tipo.choices
        }
        if tipo in tipos_validos:
            queryset = queryset.filter(tipo=tipo)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "q": self.request.GET.get("q", "").strip(),
                "tipo": self.request.GET.get("tipo", "").strip(),
                "tipos": MovimientoInventario.Tipo.choices,
                "total_movimientos": MovimientoInventario.objects.count(),
                "total_entradas": MovimientoInventario.objects.filter(
                    tipo__in=MovimientoInventario.TIPOS_ENTRADA
                ).count(),
                "total_salidas": MovimientoInventario.objects.filter(
                    tipo__in=MovimientoInventario.TIPOS_SALIDA
                ).count(),
                "total_ajustes": MovimientoInventario.objects.filter(
                    tipo__in=(
                        MovimientoInventario.Tipo.AJUSTE_POSITIVO,
                        MovimientoInventario.Tipo.AJUSTE_NEGATIVO,
                    )
                ).count(),
            }
        )

        filtros = self.request.GET.copy()
        filtros.pop("page", None)
        context["querystring"] = filtros.urlencode()
        return context


class MovimientoCreateView(RoleRequiredMixin, FormView):
    """Registro manual de una entrada, salida o ajuste de inventario."""

    allowed_groups = ADMIN_ROLES
    form_class = MovimientoForm
    template_name = "inventario/movimiento_form.html"

    def get_initial(self):
        initial = super().get_initial()
        lote_id = self.request.GET.get("lote", "").strip()
        if lote_id.isdigit():
            initial["lote"] = lote_id
        return initial

    def get_success_url(self):
        return reverse("inventario:movimientos")

    def form_valid(self, form):
        datos = form.cleaned_data
        try:
            movimiento = registrar_movimiento(
                lote=datos["lote"],
                tipo=datos["tipo"],
                cantidad=datos["cantidad"],
                usuario=self.request.user,
                motivo=datos.get("motivo", ""),
            )
        except ValidationError as error:
            _agregar_errores_al_formulario(form, error)
            return self.form_invalid(form)

        messages.success(
            self.request,
            (
                f"Se registró {movimiento.get_tipo_display().lower()} de "
                f"{movimiento.cantidad:.2f} unidades en el lote "
                f"{movimiento.lote.codigo_lote}. Stock resultante: "
                f"{movimiento.stock_resultante:.2f}."
            ),
        )
        return redirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "form_title": "Registrar movimiento",
                "form_subtitle": (
                    "Toda entrada, salida o ajuste queda registrado en el "
                    "historial y actualiza el stock del lote."
                ),
                "submit_label": "Registrar movimiento",
            }
        )
        return context
