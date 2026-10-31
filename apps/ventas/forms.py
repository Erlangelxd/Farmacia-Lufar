"""Formularios del módulo de ventas."""

from django import forms
from django.core.exceptions import ValidationError
from django.forms import BaseInlineFormSet, inlineformset_factory

from apps.catalogo.models import Producto
from apps.clientes.models import Cliente

from .models import DetalleVenta, Venta


class ProductoSelect(forms.Select):
    """Selector de productos que expone el precio para la vista previa."""

    def create_option(
        self,
        name,
        value,
        label,
        selected,
        index,
        subindex=None,
        attrs=None,
    ):
        option = super().create_option(
            name,
            value,
            label,
            selected,
            index,
            subindex=subindex,
            attrs=attrs,
        )
        if value and hasattr(value, "instance"):
            option["attrs"]["data-precio"] = f"{value.instance.precio_venta:.2f}"
        return option


class VentaForm(forms.ModelForm):
    """Datos generales de la venta."""

    class Meta:
        model = Venta
        fields = ("cliente", "metodo_pago", "monto_recibido")
        widgets = {
            "cliente": forms.Select(attrs={"class": "form-control"}),
            "metodo_pago": forms.Select(attrs={"class": "form-control"}),
            "monto_recibido": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "0",
                    "step": "0.01",
                    "inputmode": "decimal",
                    "placeholder": "0.00",
                    "data-sale-received": "",
                }
            ),
        }
        labels = {
            "cliente": "Cliente",
            "metodo_pago": "Método de pago",
            "monto_recibido": "Efectivo recibido",
        }
        help_texts = {
            "cliente": (
                "Opcional. Si no seleccionas un cliente, se registra como "
                "Consumidor final."
            ),
            "monto_recibido": (
                "Efectivo entregado por el cliente. Debe cubrir el total."
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["cliente"].queryset = Cliente.objects.filter(
            activo=True
        ).order_by("nombre")
        self.fields["cliente"].empty_label = "Consumidor final"
        self.fields["metodo_pago"].choices = Venta.MetodoPago.choices


class DetalleVentaForm(forms.ModelForm):
    """Línea de producto de la venta."""

    class Meta:
        model = DetalleVenta
        fields = ("producto", "cantidad")
        widgets = {
            "producto": ProductoSelect(
                attrs={
                    "class": "form-control",
                    "data-line-product": "",
                }
            ),
            "cantidad": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "1",
                    "max": "9999",
                    "step": "1",
                    "inputmode": "numeric",
                    "data-line-quantity": "",
                }
            ),
        }
        labels = {
            "producto": "Producto",
            "cantidad": "Cantidad",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["producto"].queryset = Producto.objects.filter(
            activo=True
        ).order_by("nombre")
        self.fields["producto"].empty_label = "Selecciona un producto"


class BaseDetalleVentaFormSet(BaseInlineFormSet):
    """Validaciones conjuntas de las líneas de venta."""

    default_error_messages = {
        **BaseInlineFormSet.default_error_messages,
        "too_few_forms": "Agrega al menos un producto a la venta.",
        "too_many_forms": "La venta tiene demasiados productos.",
    }

    def add_fields(self, form, index):
        super().add_fields(form, index)
        form.fields["DELETE"].widget.attrs.update(
            {
                "class": "sale-line__delete-input",
                "data-line-delete": "",
            }
        )

    def validate_unique(self):
        """La repetición de producto se valida en clean() con un mensaje propio."""
        return None

    def clean(self):
        super().clean()
        if any(self.errors):
            return

        productos_vistos: set[int] = set()
        for form in self.forms:
            if not form.cleaned_data or form.cleaned_data.get("DELETE"):
                continue
            producto = form.cleaned_data.get("producto")
            if producto is None:
                continue
            if producto.pk in productos_vistos:
                raise ValidationError(
                    f"El producto {producto.nombre} está repetido en la venta."
                )
            productos_vistos.add(producto.pk)


DetalleVentaFormSet = inlineformset_factory(
    Venta,
    DetalleVenta,
    form=DetalleVentaForm,
    formset=BaseDetalleVentaFormSet,
    extra=3,
    can_delete=True,
    min_num=1,
    validate_min=True,
)
