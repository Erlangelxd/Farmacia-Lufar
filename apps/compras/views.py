"""Vistas del módulo de compras."""

from decimal import Decimal

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import Count, DecimalField, Q, Sum
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import (
    CreateView,
    DetailView,
    ListView,
    UpdateView,
)

from apps.accounts.constants import ADMIN_GROUP
from apps.core.mixins import RoleRequiredMixin
from apps.inventario.models import Lote

from .forms import (
    CompraForm,
    DetalleCompraFormSet,
    ProveedorForm,
    RecepcionCompraForm,
)
from .models import Compra, Proveedor
from .services import (
    actualizar_compra,
    anular_compra,
    recibir_compra,
    registrar_compra,
)

ADMIN_ROLES = (ADMIN_GROUP,)


def _agregar_errores_al_formulario(form, error: ValidationError) -> None:
    """Vuelca los errores de un servicio de compras en el formulario."""
    if hasattr(error, "message_dict"):
        for campo, mensajes in error.message_dict.items():
            for mensaje in mensajes:
                form.add_error(campo if campo in form.fields else None, mensaje)
        return

    for mensaje in error.messages:
        form.add_error(None, mensaje)


def _lineas_desde_formset(formset) -> list[dict]:
    """Extrae las líneas válidas del formset de detalles."""
    return [
        {
            "producto": detalle_form.cleaned_data["producto"],
            "cantidad": detalle_form.cleaned_data["cantidad"],
            "costo_unitario": detalle_form.cleaned_data["costo_unitario"],
        }
        for detalle_form in formset.forms
        if detalle_form.cleaned_data
        and not detalle_form.cleaned_data.get("DELETE")
        and detalle_form.cleaned_data.get("producto")
    ]


class ComprasIndexView(RoleRequiredMixin, ListView):
    """Listado de compras con búsqueda, filtros y resumen."""

    allowed_groups = ADMIN_ROLES
    model = Compra
    template_name = "compras/compra_list.html"
    context_object_name = "compras"
    paginate_by = 20

    def get_queryset(self):
        queryset = (
            super()
            .get_queryset()
            .select_related("proveedor", "usuario")
            .prefetch_related("detalles__producto")
        )
        busqueda = self.request.GET.get("q", "").strip()
        proveedor_id = self.request.GET.get("proveedor", "").strip()
        estado = self.request.GET.get("estado", "").strip()

        if busqueda:
            filtro = (
                Q(proveedor__nombre__icontains=busqueda)
                | Q(numero_factura__icontains=busqueda)
                | Q(detalles__producto__nombre__icontains=busqueda)
                | Q(detalles__producto__codigo__icontains=busqueda)
            )
            numero = busqueda.upper()
            if numero.startswith("C-"):
                numero = numero[2:]
            if numero.isdigit() and len(numero) <= 7:
                filtro |= Q(pk=int(numero))
            queryset = queryset.filter(filtro).distinct()

        if proveedor_id.isdigit():
            queryset = queryset.filter(proveedor_id=int(proveedor_id))
        if estado in Compra.Estado.values:
            queryset = queryset.filter(estado=estado)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        hoy = timezone.localdate()
        recibidas = Compra.objects.filter(estado=Compra.Estado.RECIBIDA)
        context.update(
            {
                "q": self.request.GET.get("q", "").strip(),
                "proveedor_id": self.request.GET.get("proveedor", "").strip(),
                "estado": self.request.GET.get("estado", "").strip(),
                "proveedores": Proveedor.objects.order_by("nombre"),
                "estados": Compra.Estado.choices,
                "total_compras": Compra.objects.count(),
                "total_borradores": Compra.objects.filter(
                    estado=Compra.Estado.BORRADOR
                ).count(),
                "total_recibidas": recibidas.count(),
                "monto_recibido": (
                    recibidas.aggregate(total=Sum("total"))["total"]
                    or Decimal("0.00")
                ),
                "compras_mes": Compra.objects.filter(
                    fecha_compra__year=hoy.year,
                    fecha_compra__month=hoy.month,
                ).count(),
            }
        )

        filtros = self.request.GET.copy()
        filtros.pop("page", None)
        context["querystring"] = filtros.urlencode()
        return context


class ProveedorListView(RoleRequiredMixin, ListView):
    """Listado de proveedores con búsqueda y filtro de estado."""

    allowed_groups = ADMIN_ROLES
    model = Proveedor
    template_name = "compras/proveedor_list.html"
    context_object_name = "proveedores"
    paginate_by = 20

    def get_queryset(self):
        queryset = (
            super()
            .get_queryset()
            .annotate(
                total_compras=Count("compras", distinct=True),
                monto_recibido=Coalesce(
                    Sum(
                        "compras__total",
                        filter=Q(compras__estado=Compra.Estado.RECIBIDA),
                    ),
                    Decimal("0.00"),
                    output_field=DecimalField(max_digits=12, decimal_places=2),
                ),
            )
        )
        busqueda = self.request.GET.get("q", "").strip()
        estado = self.request.GET.get("estado", "").strip()

        if busqueda:
            queryset = queryset.filter(
                Q(nombre__icontains=busqueda)
                | Q(nit__icontains=busqueda)
                | Q(contacto__icontains=busqueda)
                | Q(telefono__icontains=busqueda)
                | Q(email__icontains=busqueda)
            )

        if estado == "activos":
            queryset = queryset.filter(activo=True)
        elif estado == "inactivos":
            queryset = queryset.filter(activo=False)

        return queryset.order_by("nombre", "pk")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "q": self.request.GET.get("q", "").strip(),
                "estado": self.request.GET.get("estado", "").strip(),
                "total_proveedores": Proveedor.objects.count(),
                "total_activos": Proveedor.objects.filter(activo=True).count(),
                "total_inactivos": Proveedor.objects.filter(
                    activo=False
                ).count(),
            }
        )

        filtros = self.request.GET.copy()
        filtros.pop("page", None)
        context["querystring"] = filtros.urlencode()
        return context


class ProveedorCreateView(RoleRequiredMixin, CreateView):
    """Registro de un proveedor nuevo."""

    allowed_groups = ADMIN_ROLES
    model = Proveedor
    form_class = ProveedorForm
    template_name = "compras/proveedor_form.html"

    def get_success_url(self):
        return reverse("compras:proveedores")

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request,
            f"El proveedor {self.object.nombre} se registró correctamente.",
        )
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "form_title": "Nuevo proveedor",
                "form_subtitle": (
                    "Registra los datos del proveedor para asociarlo a las "
                    "compras de mercadería."
                ),
                "submit_label": "Guardar proveedor",
            }
        )
        return context


class ProveedorUpdateView(RoleRequiredMixin, UpdateView):
    """Edición de los datos de un proveedor."""

    allowed_groups = ADMIN_ROLES
    model = Proveedor
    form_class = ProveedorForm
    template_name = "compras/proveedor_form.html"

    def get_success_url(self):
        return reverse("compras:proveedores")

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request,
            f"El proveedor {self.object.nombre} se actualizó correctamente.",
        )
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "form_title": f"Editar {self.object.nombre}",
                "form_subtitle": (
                    "Actualiza los datos del proveedor. Las compras ya "
                    "registradas conservan su información."
                ),
                "submit_label": "Guardar cambios",
            }
        )
        return context


class ProveedorToggleActiveView(RoleRequiredMixin, View):
    """Activa o desactiva un proveedor mediante POST."""

    allowed_groups = ADMIN_ROLES

    def post(self, request, pk):
        proveedor = get_object_or_404(Proveedor, pk=pk)
        proveedor.activo = not proveedor.activo
        proveedor.save(update_fields=["activo", "actualizado_en"])
        estado = "activado" if proveedor.activo else "desactivado"
        messages.success(
            request,
            f"El proveedor {proveedor.nombre} fue {estado}.",
        )
        return redirect("compras:proveedores")


class CompraCreateView(RoleRequiredMixin, View):
    """Registro de una compra en borrador con sus detalles."""

    allowed_groups = ADMIN_ROLES
    template_name = "compras/compra_form.html"

    def get(self, request):
        form = CompraForm(initial={"fecha_compra": timezone.localdate()})
        formset = DetalleCompraFormSet(
            instance=Compra(),
            prefix="detalles",
        )
        return self._render(request, form, formset)

    def post(self, request):
        form = CompraForm(request.POST)
        formset = DetalleCompraFormSet(
            request.POST,
            instance=Compra(),
            prefix="detalles",
        )

        if form.is_valid() and formset.is_valid():
            try:
                compra = registrar_compra(
                    proveedor=form.cleaned_data["proveedor"],
                    usuario=request.user,
                    numero_factura=form.cleaned_data["numero_factura"],
                    fecha_compra=form.cleaned_data["fecha_compra"],
                    impuesto=form.cleaned_data["impuesto"],
                    observaciones=form.cleaned_data["observaciones"],
                    lineas=_lineas_desde_formset(formset),
                )
            except ValidationError as error:
                _agregar_errores_al_formulario(form, error)
            else:
                messages.success(
                    request,
                    (
                        f"La compra {compra.numero} se registró como borrador. "
                        "Recíbela para actualizar el inventario."
                    ),
                )
                return redirect("compras:compra_detalle", pk=compra.pk)

        return self._render(request, form, formset)

    def _render(self, request, form, formset):
        return render(
            request,
            self.template_name,
            {
                "form": form,
                "formset": formset,
                "es_creacion": True,
                "form_title": "Nueva compra",
                "form_subtitle": (
                    "Registra el proveedor, los productos y sus costos. La "
                    "compra queda en borrador hasta que se reciba."
                ),
                "submit_label": "Guardar borrador",
                "compra": None,
            },
        )


class CompraUpdateView(RoleRequiredMixin, View):
    """Edición de una compra en borrador."""

    allowed_groups = ADMIN_ROLES
    template_name = "compras/compra_form.html"

    def get(self, request, pk):
        compra = get_object_or_404(Compra, pk=pk)
        if compra.estado != Compra.Estado.BORRADOR:
            messages.error(
                request,
                "Solo puedes editar compras en borrador.",
            )
            return redirect("compras:compra_detalle", pk=compra.pk)

        form = CompraForm(instance=compra)
        formset = DetalleCompraFormSet(instance=compra, prefix="detalles")
        return self._render(request, compra, form, formset)

    def post(self, request, pk):
        compra = get_object_or_404(Compra, pk=pk)
        if compra.estado != Compra.Estado.BORRADOR:
            messages.error(
                request,
                "Solo puedes editar compras en borrador.",
            )
            return redirect("compras:compra_detalle", pk=compra.pk)

        form = CompraForm(request.POST, instance=compra)
        formset = DetalleCompraFormSet(
            request.POST,
            instance=compra,
            prefix="detalles",
        )

        if form.is_valid() and formset.is_valid():
            try:
                compra = actualizar_compra(
                    compra=compra,
                    proveedor=form.cleaned_data["proveedor"],
                    numero_factura=form.cleaned_data["numero_factura"],
                    fecha_compra=form.cleaned_data["fecha_compra"],
                    impuesto=form.cleaned_data["impuesto"],
                    observaciones=form.cleaned_data["observaciones"],
                    lineas=_lineas_desde_formset(formset),
                )
            except ValidationError as error:
                _agregar_errores_al_formulario(form, error)
            else:
                messages.success(
                    request,
                    f"La compra {compra.numero} se actualizó correctamente.",
                )
                return redirect("compras:compra_detalle", pk=compra.pk)

        return self._render(request, compra, form, formset)

    def _render(self, request, compra, form, formset):
        return render(
            request,
            self.template_name,
            {
                "form": form,
                "formset": formset,
                "es_creacion": False,
                "form_title": f"Editar compra {compra.numero}",
                "form_subtitle": (
                    "Actualiza los datos y las líneas mientras la compra "
                    "siga en borrador."
                ),
                "submit_label": "Guardar cambios",
                "compra": compra,
            },
        )


class CompraDetailView(RoleRequiredMixin, DetailView):
    """Ficha de consulta de una compra y sus detalles."""

    allowed_groups = ADMIN_ROLES
    model = Compra
    template_name = "compras/compra_detail.html"
    context_object_name = "compra"

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related("proveedor", "usuario")
            .prefetch_related("detalles__producto", "detalles__lote")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "es_borrador": self.object.estado == Compra.Estado.BORRADOR,
                "es_recibida": self.object.estado == Compra.Estado.RECIBIDA,
                "es_anulada": self.object.estado == Compra.Estado.ANULADA,
            }
        )
        return context


class CompraRecepcionView(RoleRequiredMixin, View):
    """Recepción de una compra: asigna lotes y registra entradas."""

    allowed_groups = ADMIN_ROLES
    template_name = "compras/compra_recepcion.html"

    def _obtener_compra(self, pk):
        return get_object_or_404(
            Compra.objects.select_related("proveedor").prefetch_related(
                "detalles__producto",
                "detalles__lote",
            ),
            pk=pk,
        )

    def get(self, request, pk):
        compra = self._obtener_compra(pk)
        if compra.estado != Compra.Estado.BORRADOR:
            messages.error(
                request,
                "Solo puedes recibir compras en borrador.",
            )
            return redirect("compras:compra_detalle", pk=compra.pk)

        form = RecepcionCompraForm(compra=compra)
        return self._render(request, compra, form)

    def post(self, request, pk):
        compra = self._obtener_compra(pk)
        if compra.estado != Compra.Estado.BORRADOR:
            messages.error(
                request,
                "Solo puedes recibir compras en borrador.",
            )
            return redirect("compras:compra_detalle", pk=compra.pk)

        form = RecepcionCompraForm(request.POST, compra=compra)
        if form.is_valid():
            lotes = {
                detalle.pk: form.cleaned_data[form.nombre_campo(detalle)]
                for detalle in form.detalles
            }
            try:
                compra = recibir_compra(
                    compra=compra,
                    usuario=request.user,
                    lotes_por_detalle=lotes,
                )
            except ValidationError as error:
                _agregar_errores_al_formulario(form, error)
            else:
                messages.success(
                    request,
                    (
                        f"La compra {compra.numero} se recibió y el "
                        "inventario se actualizó correctamente."
                    ),
                )
                return redirect("compras:compra_detalle", pk=compra.pk)

        return self._render(request, compra, form)

    def _render(self, request, compra, form):
        filas = [
            {
                "detalle": detalle,
                "campo": form[form.nombre_campo(detalle)],
            }
            for detalle in form.detalles
        ]

        productos = {detalle.producto_id for detalle in form.detalles}
        con_lotes = set(
            Lote.objects.filter(
                producto_id__in=productos,
                activo=True,
            ).values_list("producto_id", flat=True)
        )
        faltan_lotes = []
        vistos = set()
        for detalle in form.detalles:
            if (
                detalle.producto_id not in con_lotes
                and detalle.producto_id not in vistos
            ):
                vistos.add(detalle.producto_id)
                faltan_lotes.append(detalle.producto)

        return render(
            request,
            self.template_name,
            {
                "compra": compra,
                "form": form,
                "filas": filas,
                "faltan_lotes": faltan_lotes,
            },
        )


class CompraAnularView(RoleRequiredMixin, View):
    """Anula una compra en borrador sin afectar inventario."""

    allowed_groups = ADMIN_ROLES

    def post(self, request, pk):
        compra = get_object_or_404(Compra, pk=pk)
        try:
            compra = anular_compra(compra=compra)
        except ValidationError as error:
            for mensaje in error.messages:
                messages.error(request, mensaje)
        else:
            messages.success(
                request,
                f"La compra {compra.numero} fue anulada.",
            )
        return redirect("compras:compra_detalle", pk=compra.pk)
