"""Formularios del módulo de compras."""

from django import forms
from django.db.models import Q
from django.forms import BaseInlineFormSet, inlineformset_factory

from apps.catalogo.models import Producto
from apps.inventario.models import Lote

from .models import Compra, DetalleCompra, Proveedor


class ProveedorForm(forms.ModelForm):
    """Registro y edición de proveedores."""

    class Meta:
        model = Proveedor
        fields = (
            "nombre",
            "nit",
            "telefono",
            "email",
            "direccion",
            "contacto",
            "activo",
        )
        widgets = {
            "nombre": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Ej. Distribuidora Farmacéutica S.A.",
                    "autocomplete": "off",
                    "autofocus": True,
                }
            ),
            "nit": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Ej. 123456789",
                    "autocomplete": "off",
                }
            ),
            "telefono": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Ej. 70000000",
                }
            ),
            "email": forms.EmailInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Ej. contacto@proveedor.com",
                }
            ),
            "direccion": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Calle, número y ciudad",
                }
            ),
            "contacto": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Nombre de la persona de contacto",
                }
            ),
            "activo": forms.CheckboxInput(attrs={"class": "checkbox-control"}),
        }
        labels = {
            "nombre": "Nombre o razón social",
            "nit": "NIT",
            "telefono": "Teléfono",
            "email": "Correo electrónico",
            "direccion": "Dirección",
            "contacto": "Persona de contacto",
            "activo": "Proveedor activo",
        }
        help_texts = {
            "nit": "Opcional. Si se informa, debe ser único.",
            "email": "Opcional.",
            "direccion": "Opcional.",
            "contacto": "Opcional.",
            "activo": (
                "Solo los proveedores activos aparecen al registrar compras."
            ),
        }

    def clean_nombre(self) -> str:
        nombre = " ".join((self.cleaned_data.get("nombre") or "").split())
        if not nombre:
            raise forms.ValidationError(
                "Ingresa el nombre o razón social."
            )
        return nombre

    def clean_nit(self) -> str:
        nit = (self.cleaned_data.get("nit") or "").strip().upper()
        if nit:
            existentes = Proveedor.objects.filter(nit__iexact=nit)
            if self.instance.pk:
                existentes = existentes.exclude(pk=self.instance.pk)
            if existentes.exists():
                raise forms.ValidationError(
                    "Ya existe un proveedor con ese NIT."
                )
        return nit


class CompraForm(forms.ModelForm):
    """Datos generales de una compra."""

    class Meta:
        model = Compra
        fields = (
            "proveedor",
            "numero_factura",
            "fecha_compra",
            "impuesto",
            "observaciones",
        )
        widgets = {
            "proveedor": forms.Select(attrs={"class": "form-control"}),
            "numero_factura": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Ej. F-001",
                    "autocomplete": "off",
                }
            ),
            "fecha_compra": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "impuesto": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "0",
                    "step": "0.01",
                    "inputmode": "decimal",
                    "placeholder": "0.00",
                    "data-compra-tax": "",
                }
            ),
            "observaciones": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Observaciones opcionales de la compra",
                }
            ),
        }
        labels = {
            "proveedor": "Proveedor",
            "numero_factura": "Número de factura",
            "fecha_compra": "Fecha de compra",
            "impuesto": "Impuesto",
            "observaciones": "Observaciones",
        }
        help_texts = {
            "proveedor": "Solo se muestran los proveedores activos.",
            "numero_factura": "Opcional.",
            "impuesto": (
                "Monto fijo en bolivianos. El subtotal y el total se "
                "calculan con las líneas."
            ),
            "observaciones": "Opcional.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # El impuesto es un monto fijo opcional; el servicio lo normaliza a 0.
        self.fields["impuesto"].required = False
        proveedores = Proveedor.objects.filter(activo=True)
        if self.instance.pk and self.instance.proveedor_id:
            proveedores = Proveedor.objects.filter(
                Q(activo=True) | Q(pk=self.instance.proveedor_id)
            )
        self.fields["proveedor"].queryset = proveedores.order_by("nombre")


class DetalleCompraForm(forms.ModelForm):
    """Línea de producto de una compra."""

    class Meta:
        model = DetalleCompra
        fields = ("producto", "cantidad", "costo_unitario")
        widgets = {
            "producto": forms.Select(
                attrs={
                    "class": "form-control",
                    "data-compra-product": "",
                }
            ),
            "cantidad": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "1",
                    "max": "9999",
                    "step": "1",
                    "inputmode": "numeric",
                    "data-compra-quantity": "",
                }
            ),
            "costo_unitario": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "0",
                    "step": "0.01",
                    "inputmode": "decimal",
                    "placeholder": "0.00",
                    "data-compra-cost": "",
                }
            ),
        }
        labels = {
            "producto": "Producto",
            "cantidad": "Cantidad",
            "costo_unitario": "Costo unitario",
        }
        help_texts = {
            "costo_unitario": "Costo de una unidad, sin impuestos.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        productos = Producto.objects.filter(activo=True)
        if self.instance.pk and self.instance.producto_id:
            productos = Producto.objects.filter(
                Q(activo=True) | Q(pk=self.instance.producto_id)
            )
        self.fields["producto"].queryset = productos.order_by("nombre")
        self.fields["producto"].empty_label = "Selecciona un producto"


class BaseDetalleCompraFormSet(BaseInlineFormSet):
    """Validaciones conjuntas de las líneas de compra."""

    default_error_messages = {
        **BaseInlineFormSet.default_error_messages,
        "too_few_forms": "Agrega al menos un producto a la compra.",
        "too_many_forms": "La compra tiene demasiados productos.",
    }

    def add_fields(self, form, index):
        super().add_fields(form, index)
        form.fields["DELETE"].widget.attrs.update(
            {
                "class": "sale-line__delete-input",
                "data-compra-delete": "",
            }
        )

    def clean(self):
        super().clean()
        if any(self.errors):
            return

        # La repetición de producto está permitida: una compra puede separar
        # el mismo producto en varias líneas para asignar lotes distintos.
        if not any(
            form.cleaned_data
            and not form.cleaned_data.get("DELETE")
            and form.cleaned_data.get("producto")
            for form in self.forms
        ):
            raise forms.ValidationError(
                "Agrega al menos un producto a la compra."
            )


DetalleCompraFormSet = inlineformset_factory(
    Compra,
    DetalleCompra,
    form=DetalleCompraForm,
    formset=BaseDetalleCompraFormSet,
    extra=3,
    can_delete=True,
    min_num=1,
    validate_min=True,
)


class RecepcionCompraForm(forms.Form):
    """Selecciona el lote existente que recibe cada línea de la compra."""

    def __init__(self, *args, compra: Compra, **kwargs):
        super().__init__(*args, **kwargs)
        self.compra = compra
        self.detalles = list(
            compra.detalles.select_related("producto", "lote").order_by("pk")
        )

        for detalle in self.detalles:
            campo = self.nombre_campo(detalle)
            self.fields[campo] = forms.ModelChoiceField(
                label=detalle.producto.nombre,
                queryset=Lote.objects.filter(
                    producto=detalle.producto,
                    activo=True,
                ).order_by("fecha_vencimiento", "codigo_lote", "pk"),
                required=True,
                empty_label="Selecciona un lote",
                widget=forms.Select(attrs={"class": "form-control"}),
                help_text=(
                    f"Cantidad a recibir: {detalle.cantidad} "
                    f"{detalle.producto.unidad_medida.lower()}."
                ),
            )
            if detalle.lote_id:
                self.initial[campo] = detalle.lote_id

    @staticmethod
    def nombre_campo(detalle: DetalleCompra) -> str:
        return f"lote_{detalle.pk}"

    def clean(self):
        cleaned_data = super().clean()
        lotes_vistos: set[int] = set()

        for detalle in self.detalles:
            campo = self.nombre_campo(detalle)
            lote = cleaned_data.get(campo)
            if lote is None:
                continue

            if lote.producto_id != detalle.producto_id:
                self.add_error(
                    campo,
                    "El lote seleccionado no corresponde al producto de la línea.",
                )
                continue
            if not lote.activo:
                self.add_error(campo, "El lote seleccionado no está activo.")
                continue
            if lote.pk in lotes_vistos:
                self.add_error(
                    campo,
                    f"El lote {lote.codigo_lote} ya se seleccionó en otra línea.",
                )
                continue
            lotes_vistos.add(lote.pk)

        return cleaned_data
