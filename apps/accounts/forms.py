"""Formularios de autenticación."""

from django import forms
from django.contrib.auth.forms import AuthenticationForm


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
