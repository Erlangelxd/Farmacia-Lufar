"""Formularios del catálogo de productos y categorías."""

from django import forms
from django.db.models import Q

from .models import Categoria, Producto


class ProductoForm(forms.ModelForm):
    """Registro y edición de productos del catálogo."""

    class Meta:
        model = Producto
        fields = (
            "codigo",
            "nombre",
            "categoria",
            "laboratorio",
            "forma_farmaceutica",
            "presentacion",
            "principio_activo",
            "concentracion",
            "unidad_medida",
            "precio_venta",
            "stock_minimo",
            "descripcion",
            "activo",
        )
        widgets = {
            "codigo": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Ej. P-001",
                    "autocomplete": "off",
                    "autofocus": True,
                }
            ),
            "nombre": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Ej. Paracetamol 500 mg",
                    "autocomplete": "off",
                }
            ),
            "categoria": forms.Select(attrs={"class": "form-control"}),
            "laboratorio": forms.Select(attrs={"class": "form-control"}),
            "forma_farmaceutica": forms.Select(attrs={"class": "form-control"}),
            "presentacion": forms.Select(attrs={"class": "form-control"}),
            "principio_activo": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Ej. Paracetamol",
                    "autocomplete": "off",
                }
            ),
            "concentracion": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Ej. 500 mg",
                    "autocomplete": "off",
                }
            ),
            "unidad_medida": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Ej. UNIDAD",
                    "autocomplete": "off",
                }
            ),
            "precio_venta": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "0",
                    "step": "0.01",
                    "placeholder": "0.00",
                }
            ),
            "stock_minimo": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "0",
                    "step": "1",
                    "placeholder": "0",
                }
            ),
            "descripcion": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Detalles opcionales del producto",
                }
            ),
            "activo": forms.CheckboxInput(attrs={"class": "checkbox-control"}),
        }
        labels = {
            "codigo": "Código",
            "nombre": "Nombre del producto",
            "categoria": "Categoría",
            "laboratorio": "Laboratorio",
            "forma_farmaceutica": "Forma farmacéutica",
            "presentacion": "Presentación",
            "principio_activo": "Principio activo",
            "concentracion": "Concentración",
            "unidad_medida": "Unidad de medida",
            "precio_venta": "Precio de venta (Bs)",
            "stock_minimo": "Stock mínimo",
            "descripcion": "Descripción",
            "activo": "Producto activo",
        }
        help_texts = {
            "codigo": "Se guarda en mayúsculas y debe ser único.",
            "categoria": "Solo se muestran las categorías activas.",
            "laboratorio": "Opcional. Se administra desde Django Admin.",
            "forma_farmaceutica": "Opcional. Se administra desde Django Admin.",
            "presentacion": "Opcional. Se administra desde Django Admin.",
            "unidad_medida": "Ej. UNIDAD, CAJA, FRASCO.",
            "precio_venta": "Precio unitario de venta al público.",
            "stock_minimo": "Umbral para las alertas de reposición de inventario.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in (
            "categoria",
            "laboratorio",
            "forma_farmaceutica",
            "presentacion",
        ):
            field = self.fields[field_name]
            queryset = field.queryset

            # Solo categorías y laboratorios tienen estado propio; las formas
            # farmacéuticas y presentaciones se administran desde Django Admin.
            if field_name in ("categoria", "laboratorio"):
                queryset = queryset.filter(activo=True)
                actual = getattr(self.instance, f"{field_name}_id", None)
                if self.instance.pk and actual:
                    queryset = field.queryset.filter(
                        Q(activo=True) | Q(pk=actual)
                    )

            field.queryset = queryset.order_by("nombre")

    def clean_codigo(self) -> str:
        codigo = (self.cleaned_data.get("codigo") or "").strip().upper()
        if not codigo:
            return codigo
        existentes = Producto.objects.filter(codigo__iexact=codigo)
        if self.instance.pk:
            existentes = existentes.exclude(pk=self.instance.pk)
        if existentes.exists():
            raise forms.ValidationError(
                "Ya existe un producto con ese código."
            )
        return codigo

    def clean_nombre(self) -> str:
        nombre = " ".join((self.cleaned_data.get("nombre") or "").split())
        if not nombre:
            raise forms.ValidationError("Ingresa el nombre del producto.")
        return nombre

    def clean_principio_activo(self) -> str:
        return " ".join(
            (self.cleaned_data.get("principio_activo") or "").split()
        )

    def clean_concentracion(self) -> str:
        return " ".join(
            (self.cleaned_data.get("concentracion") or "").split()
        )

    def clean_unidad_medida(self) -> str:
        return " ".join(
            (self.cleaned_data.get("unidad_medida") or "").split()
        ).upper()


class CategoriaForm(forms.ModelForm):
    """Registro y edición de categorías de productos."""

    class Meta:
        model = Categoria
        fields = ("nombre", "descripcion", "activo")
        widgets = {
            "nombre": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Ej. Analgésicos",
                    "autocomplete": "off",
                    "autofocus": True,
                }
            ),
            "descripcion": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Descripción opcional de la categoría",
                }
            ),
            "activo": forms.CheckboxInput(attrs={"class": "checkbox-control"}),
        }
        labels = {
            "nombre": "Nombre de la categoría",
            "descripcion": "Descripción",
            "activo": "Categoría activa",
        }
        help_texts = {
            "nombre": "Debe ser único, sin distinguir mayúsculas.",
            "descripcion": "Opcional. Ayuda a identificar el grupo de productos.",
            "activo": (
                "Una categoría con productos activos no puede desactivarse."
            ),
        }

    def clean_nombre(self) -> str:
        nombre = " ".join((self.cleaned_data.get("nombre") or "").split())
        if not nombre:
            raise forms.ValidationError("Ingresa el nombre de la categoría.")
        existentes = Categoria.objects.filter(nombre__iexact=nombre)
        if self.instance.pk:
            existentes = existentes.exclude(pk=self.instance.pk)
        if existentes.exists():
            raise forms.ValidationError(
                "Ya existe una categoría con ese nombre."
            )
        return nombre
