from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import Usuario


class RegistroForm(UserCreationForm):
    class Meta:
        model = Usuario
        fields = ("username", "first_name", "last_name", "email")
        labels = {
            "username": "Nombre de usuario",
            "first_name": "Nombre",
            "last_name": "Apellido",
        }

    def clean_username(self):
        value = self.cleaned_data["username"].strip().lower()
        if Usuario.objects.filter(username__iexact=value).exists():
            raise forms.ValidationError("Ese nombre de usuario ya está en uso.")
        return value

    def clean_email(self):
        value = self.cleaned_data["email"].strip().lower()
        if Usuario.objects.filter(email__iexact=value).exists():
            raise forms.ValidationError(
                "Ese correo ya está registrado. Contactá al administrador."
            )
        return value

    def save(self, commit=True):
        user = super().save(commit=False)
        # Solo se aceptan los campos del formulario; nunca privilegios enviados por el navegador.
        user.is_active = False
        user.estado = Usuario.Estado.PENDIENTE
        if commit:
            user.save()
        return user


class AccesoForm(AuthenticationForm):
    error_messages = {
        "invalid_login": "No pudimos iniciar sesión. Revisá tus datos o consultá si tu cuenta fue aprobada.",
        "inactive": "La cuenta no está habilitada. Contactá al administrador.",
    }

    def clean_username(self):
        return self.cleaned_data["username"].strip().lower()
