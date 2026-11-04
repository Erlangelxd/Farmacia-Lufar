"""Formularios de autenticación y administración de usuarios."""

from django import forms
from django.contrib.auth import get_user_model, password_validation
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError

from .constants import ADMIN_GROUP, DEFAULT_GROUPS, SELLER_GROUP

User = get_user_model()

ROLE_CHOICES = (
    (ADMIN_GROUP, "Administrador"),
    (SELLER_GROUP, "Vendedor"),
)


class LoginForm(AuthenticationForm):
    """Formulario de inicio de sesión con estilos del sistema.

    Mantiene la validación y el mecanismo de autenticación de Django; solo
    personaliza las etiquetas y los atributos de los widgets.
    """

    username = forms.CharField(
        label="Usuario",
        widget=forms.TextInput(
            attrs={
                "class": "login-input",
                "autocomplete": "username",
                "placeholder": "Usuario",
                "autocapitalize": "none",
                "spellcheck": "false",
                "autofocus": True,
            }
        ),
    )
    password = forms.CharField(
        label="Contraseña",
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "class": "login-input",
                "autocomplete": "current-password",
                "placeholder": "Contraseña",
            }
        ),
    )


class _RoleFormMixin:
    """Utilidades compartidas para asignar el rol del usuario."""

    def _save_role(self, user):
        """Deja un único rol base sin borrar otros grupos personalizados."""
        group, _ = Group.objects.get_or_create(
            name=self.cleaned_data["role"]
        )
        user.groups.remove(
            *Group.objects.filter(name__in=DEFAULT_GROUPS)
        )
        user.groups.add(group)


class UserCreateForm(_RoleFormMixin, UserCreationForm):
    """Alta de una cuenta con su rol base."""

    role = forms.ChoiceField(
        label="Rol",
        choices=ROLE_CHOICES,
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    is_active = forms.BooleanField(
        label="Cuenta activa",
        required=False,
        initial=True,
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "first_name", "last_name", "email")
        labels = {
            "username": "Nombre de usuario",
            "first_name": "Nombre",
            "last_name": "Apellido",
            "email": "Correo electrónico",
        }
        widgets = {
            "username": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "autocomplete": "username",
                    "autocapitalize": "none",
                }
            ),
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "last_name": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(
                attrs={"class": "form-control", "autocomplete": "email"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["password1"].widget.attrs.update(
            {"class": "form-control", "autocomplete": "new-password"}
        )
        self.fields["password2"].widget.attrs.update(
            {"class": "form-control", "autocomplete": "new-password"}
        )
        self.fields["is_active"].widget.attrs.update(
            {"class": "checkbox-control"}
        )
        self.fields["is_active"].initial = True

    def save(self, commit=True):
        user = super().save(commit=False)
        user.is_active = self.cleaned_data["is_active"]
        if commit:
            user.save()
            self._save_role(user)
        return user


class UserUpdateForm(_RoleFormMixin, forms.ModelForm):
    """Edición de datos, rol, estado y contraseña de una cuenta."""

    role = forms.ChoiceField(
        label="Rol",
        choices=ROLE_CHOICES,
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    nueva_password1 = forms.CharField(
        label="Nueva contraseña",
        required=False,
        strip=False,
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "autocomplete": "new-password"}
        ),
        help_text=(
            "Déjala en blanco para conservar la contraseña actual."
        ),
    )
    nueva_password2 = forms.CharField(
        label="Confirmar nueva contraseña",
        required=False,
        strip=False,
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "autocomplete": "new-password"}
        ),
    )

    class Meta:
        model = User
        fields = (
            "username",
            "first_name",
            "last_name",
            "email",
            "is_active",
        )
        labels = {
            "username": "Nombre de usuario",
            "first_name": "Nombre",
            "last_name": "Apellido",
            "email": "Correo electrónico",
            "is_active": "Cuenta activa",
        }
        widgets = {
            "username": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "autocomplete": "username",
                    "autocapitalize": "none",
                }
            ),
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "last_name": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(
                attrs={"class": "form-control", "autocomplete": "email"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["is_active"].widget.attrs.update(
            {"class": "checkbox-control"}
        )
        rol_actual = (
            self.instance.groups.filter(name__in=DEFAULT_GROUPS)
            .values_list("name", flat=True)
            .first()
        )
        if rol_actual:
            self.fields["role"].initial = rol_actual

    def clean_username(self):
        username = self.cleaned_data.get("username")
        if username and (
            User.objects.filter(username__iexact=username)
            .exclude(pk=self.instance.pk)
            .exists()
        ):
            raise ValidationError("Ya existe un usuario con ese nombre.")
        return username

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("nueva_password1")
        password2 = cleaned_data.get("nueva_password2")

        if password1 or password2:
            if password1 != password2:
                self.add_error(
                    "nueva_password2",
                    "Las contraseñas no coinciden.",
                )
            else:
                try:
                    password_validation.validate_password(
                        password1, self.instance
                    )
                except ValidationError as error:
                    self.add_error("nueva_password1", error)
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get("nueva_password1")
        if password:
            user.set_password(password)
        if commit:
            user.save()
            self._save_role(user)
        return user
