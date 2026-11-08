"""Formularios del módulo de inventario."""

from decimal import Decimal

from django import forms
from django.db.models import Q

from .models import Lote, MovimientoInventario
from .services import TIPOS_MANUALES


class LoteForm(forms.ModelForm):
    """Registro y edición de lotes.

    El stock solo se puede indicar al crear el lote. Después, cualquier cambio
    de existencias debe registrarse como movimiento.
    """

    stock_inicial = forms.DecimalField(
        label="Stock inicial",
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("0.00"),
        initial=Decimal("0.00"),
        required=False,
        widget=forms.NumberInput(
            attrs={
                "class": "form-control",
                "min": "0",
                "step": "0.01",
                "placeholder": "0.00",
            }
        ),
        help_text=(
            "Si es mayor que cero, se registrará un movimiento de inventario "
            "inicial."
        ),
    )
    costo_unitario_inicial = forms.DecimalField(
        label="Costo unitario de adquisición",
        max_digits=10,
        decimal_places=2,
        min_value=Decimal("0.00"),
        required=False,
        widget=forms.NumberInput(
            attrs={
                "class": "form-control",
                "min": "0",
                "step": "0.01",
                "placeholder": "0.00",
            }
        ),
        help_text=(
            "Se registra como costo real del lote y se usa para calcular "
            "la ganancia en ventas."
        ),
    )
    costo_unitario_existencia = forms.DecimalField(
        label="Costo unitario de las unidades actuales",
        max_digits=10,
        decimal_places=2,
        min_value=Decimal("0.00"),
        required=False,
        widget=forms.NumberInput(
            attrs={
                "class": "form-control",
                "min": "0",
                "step": "0.01",
                "placeholder": "0.00",
            }
        ),
        help_text=(
            "Solo se aplica a unidades actuales cuyo costo aún no está "
            "registrado. El ajuste queda en el historial."
        ),
    )

    field_order = (
        "producto",
        "codigo_lote",
        "fecha_fabricacion",
        "fecha_vencimiento",
        "fecha_ingreso",
        "stock_inicial",
        "costo_unitario_inicial",
        "costo_unitario_existencia",
        "activo",
    )

    class Meta:
        model = Lote
        fields = (
            "producto",
            "codigo_lote",
            "fecha_fabricacion",
            "fecha_vencimiento",
            "fecha_ingreso",
            "activo",
        )
        widgets = {
            "producto": forms.Select(attrs={"class": "form-control"}),
            "codigo_lote": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Ej. L-2026-001",
                    "autocomplete": "off",
                    "autofocus": True,
                }
            ),
            "fecha_fabricacion": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "fecha_vencimiento": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "fecha_ingreso": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "activo": forms.CheckboxInput(attrs={"class": "checkbox-control"}),
        }
        labels = {
            "producto": "Producto",
            "codigo_lote": "Código de lote",
            "fecha_fabricacion": "Fecha de fabricación",
            "fecha_vencimiento": "Fecha de vencimiento",
            "fecha_ingreso": "Fecha de ingreso",
            "activo": "Lote activo",
        }
        help_texts = {
            "producto": "Solo se muestran los productos activos.",
            "codigo_lote": (
                "Se guarda en mayúsculas y debe ser único por producto."
            ),
            "fecha_fabricacion": "Opcional.",
            "fecha_vencimiento": (
                "Opcional. Se usa para las alertas de vencimiento."
            ),
            "fecha_ingreso": "Fecha en la que el lote entra al inventario.",
            "activo": (
                "Un lote con existencias no puede desactivarse."
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        productos = self.fields["producto"].queryset.filter(activo=True)
        if self.instance.pk and self.instance.producto_id:
            productos = self.fields["producto"].queryset.filter(
                Q(activo=True) | Q(pk=self.instance.producto_id)
            )
        self.fields["producto"].queryset = productos.order_by("nombre")

        # El stock no se edita: los cambios posteriores son movimientos.
        if self.instance.pk:
            self.fields.pop("stock_inicial", None)
            self.fields.pop("costo_unitario_inicial", None)
        else:
            self.fields.pop("costo_unitario_existencia", None)

    def clean_codigo_lote(self) -> str:
        codigo = (self.cleaned_data.get("codigo_lote") or "").strip().upper()
        if not codigo:
            raise forms.ValidationError("Ingresa el código del lote.")

        producto = self.cleaned_data.get("producto")
        if producto is not None:
            existentes = Lote.objects.filter(
                producto=producto,
                codigo_lote__iexact=codigo,
            )
            if self.instance.pk:
                existentes = existentes.exclude(pk=self.instance.pk)
            if existentes.exists():
                raise forms.ValidationError(
                    "El producto ya tiene un lote con ese código."
                )
        return codigo

    def clean(self):
        cleaned_data = super().clean()

        fabricacion = cleaned_data.get("fecha_fabricacion")
        vencimiento = cleaned_data.get("fecha_vencimiento")
        if fabricacion and vencimiento and fabricacion > vencimiento:
            self.add_error(
                "fecha_vencimiento",
                (
                    "La fecha de vencimiento debe ser posterior a la fecha "
                    "de fabricación."
                ),
            )

        stock_inicial = cleaned_data.get("stock_inicial")
        costo_unitario = cleaned_data.get("costo_unitario_inicial")
        if (
            not self.instance.pk
            and stock_inicial
            and stock_inicial > Decimal("0.00")
            and costo_unitario is None
        ):
            self.add_error(
                "costo_unitario_inicial",
                "Ingresa el costo unitario de adquisición del stock inicial.",
            )
        if (
            not self.instance.pk
            and not cleaned_data.get("activo")
            and stock_inicial
            and stock_inicial > Decimal("0.00")
        ):
            self.add_error(
                "activo",
                (
                    "No puedes crear un lote inactivo con stock inicial. "
                    "Actívalo o registra el stock como movimiento."
                ),
            )

        return cleaned_data


class LoteChoiceField(forms.ModelChoiceField):
    """Muestra producto, código y stock actual en el selector de lotes."""

    def label_from_instance(self, obj: Lote) -> str:
        return (
            f"{obj.producto.nombre} — {obj.codigo_lote} "
            f"(stock: {obj.stock_actual:.2f})"
        )


class MovimientoForm(forms.Form):
    """Registro manual de entradas, salidas y ajustes de inventario."""

    lote = LoteChoiceField(
        label="Lote",
        queryset=Lote.objects.none(),
        widget=forms.Select(attrs={"class": "form-control"}),
        help_text="Solo se muestran lotes activos de productos activos.",
    )
    tipo = forms.ChoiceField(
        label="Tipo de movimiento",
        choices=[
            choice for choice in MovimientoInventario.Tipo.choices
            if choice[0] in TIPOS_MANUALES
        ],
        initial=MovimientoInventario.Tipo.ENTRADA,
        widget=forms.Select(attrs={"class": "form-control"}),
        help_text=(
            "Entradas y ajustes positivos aumentan el stock; salidas y "
            "ajustes negativos lo reducen."
        ),
    )
    cantidad = forms.DecimalField(
        label="Cantidad",
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("0.01"),
        widget=forms.NumberInput(
            attrs={
                "class": "form-control",
                "min": "0.01",
                "step": "0.01",
                "placeholder": "0.00",
            }
        ),
    )
    costo_unitario = forms.DecimalField(
        label="Costo unitario de adquisición",
        max_digits=10,
        decimal_places=2,
        min_value=Decimal("0.00"),
        required=False,
        widget=forms.NumberInput(
            attrs={
                "class": "form-control",
                "min": "0",
                "step": "0.01",
                "placeholder": "0.00",
            }
        ),
        help_text="Obligatorio para entradas y ajustes positivos.",
    )
    motivo = forms.CharField(
        label="Motivo",
        max_length=200,
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Ej. Compra a proveedor, merma, corrección",
            }
        ),
        help_text="Opcional. Ayuda a explicar el origen del movimiento.",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["lote"].queryset = (
            Lote.objects.filter(activo=True, producto__activo=True)
            .select_related("producto")
            .order_by("producto__nombre", "fecha_vencimiento", "pk")
        )

    def clean(self):
        cleaned_data = super().clean()

        lote = cleaned_data.get("lote")
        tipo = cleaned_data.get("tipo")
        cantidad = cleaned_data.get("cantidad")
        costo_unitario = cleaned_data.get("costo_unitario")

        if tipo in MovimientoInventario.TIPOS_ENTRADA and costo_unitario is None:
            self.add_error(
                "costo_unitario",
                "Ingresa el costo unitario de adquisición de las unidades.",
            )

        if (
            lote is not None
            and tipo in MovimientoInventario.TIPOS_SALIDA
            and cantidad is not None
            and cantidad > lote.stock_actual
        ):
            self.add_error(
                "cantidad",
                (
                    f"El lote solo tiene {lote.stock_actual:.2f} unidades "
                    "disponibles."
                ),
            )

        return cleaned_data
