from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models
from django.db.models.functions import Lower


def normalizar(valor):
    return (valor or "").strip().lower()


class AdministradorUsuarios(UserManager):
    def _create_user(self, username, email, password, **extra_fields):
        if not normalizar(email):
            raise ValueError("El correo electrónico es obligatorio.")
        return super()._create_user(username, email, password, **extra_fields)

    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields.update(is_active=True, estado=Usuario.Estado.APROBADO)
        return super().create_superuser(username, email, password, **extra_fields)

    def get_by_natural_key(self, username):
        # El login no distingue mayúsculas, igual que la unicidad en la base.
        return self.get(username__iexact=normalizar(username))


class Usuario(AbstractUser):
    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        APROBADO = "aprobado", "Aprobado"
        RECHAZADO = "rechazado", "Rechazado"

    email = models.EmailField("correo electrónico", unique=True)
    is_active = models.BooleanField("puede ingresar", default=False)
    estado = models.CharField(
        max_length=12, choices=Estado.choices, default=Estado.PENDIENTE
    )
    objects = AdministradorUsuarios()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                Lower("email"), name="usuario_email_sin_mayusculas"
            ),
            models.UniqueConstraint(
                Lower("username"), name="usuario_nombre_sin_mayusculas"
            ),
            models.CheckConstraint(
                condition=models.Q(is_active=False)
                | models.Q(estado="aprobado"),
                name="activo_solo_aprobado",
                violation_error_message=(
                    "Solo una cuenta aprobada puede ingresar. "
                    "Aprobala desde Solicitudes de acceso."
                ),
            ),
        ]

    def clean(self):
        super().clean()
        self.username = normalizar(self.username)
        self.email = normalizar(self.email)

    def save(self, *args, **kwargs):
        # Se normaliza siempre: admin, formularios, API, shell o create_user.
        self.username = normalizar(self.username)
        self.email = normalizar(self.email)
        super().save(*args, **kwargs)
