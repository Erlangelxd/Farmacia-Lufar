"""Formularios del módulo de clientes."""

from django import forms

from .models import Cliente


class ClienteForm(forms.ModelForm):
    """Registro y validación de clientes."""

    class Meta:
        model = Cliente
        fields = (
            "nombre",
            "tipo_documento",
            "numero_documento",
            "telefono",
            "activo",
        )
        widgets = {
            "nombre": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Nombre completo o razón social",
                    "autocomplete": "name",
                    "autofocus": True,
                }
            ),
            "tipo_documento": forms.Select(
                attrs={
                    "class": "form-control",
                }
            ),
            "numero_documento": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Ej. 12345678",
                    "autocomplete": "off",
                }
            ),
            "telefono": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Ej. 71234567",
                    "autocomplete": "tel",
                }
            ),
            "activo": forms.CheckboxInput(
                attrs={
                    "class": "checkbox-control",
                }
            ),
        }
        labels = {
            "nombre": "Nombre completo o razón social",
            "tipo_documento": "Tipo de documento",
            "numero_documento": "Número de documento",
            "telefono": "Teléfono",
            "activo": "Cliente activo",
        }
        help_texts = {
            "tipo_documento": (
                "Opcional. Déjalo vacío si el cliente no presenta documento."
            ),
            "numero_documento": (
                "Opcional. Si lo ingresas, debe ser único para el tipo de documento."
            ),
            "telefono": "Opcional. Se usa para búsquedas y contacto.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["tipo_documento"].choices = [
            ("", "Sin documento"),
            *Cliente.TipoDocumento.choices,
        ]

    def clean_nombre(self) -> str:
        nombre = " ".join(self.cleaned_data["nombre"].split())
        if not nombre:
            raise forms.ValidationError("Ingresa el nombre del cliente.")
        return nombre

    def clean_numero_documento(self) -> str:
        return (self.cleaned_data.get("numero_documento") or "").strip()

    def clean_telefono(self) -> str:
        return (self.cleaned_data.get("telefono") or "").strip()

    def clean(self):
        cleaned_data = super().clean()
        tipo_documento = cleaned_data.get("tipo_documento")
        numero_documento = cleaned_data.get("numero_documento")

        # Si un campo ya falló, se deja que el formulario muestre ese error
        # antes de validar la combinación.
        if "tipo_documento" in self.errors or "numero_documento" in self.errors:
            return cleaned_data

        if numero_documento and not tipo_documento:
            self.add_error(
                "tipo_documento",
                "Selecciona el tipo de documento.",
            )
        elif tipo_documento and not numero_documento:
            self.add_error(
                "numero_documento",
                "Ingresa el número de documento.",
            )
        elif tipo_documento and numero_documento:
            existentes = Cliente.objects.filter(
                tipo_documento=tipo_documento,
                numero_documento__iexact=numero_documento,
            )
            if self.instance.pk:
                existentes = existentes.exclude(pk=self.instance.pk)
            if existentes.exists():
                self.add_error(
                    "numero_documento",
                    "Ya existe un cliente con ese tipo y número de documento.",
                )

        return cleaned_data
