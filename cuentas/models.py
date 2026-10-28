from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models
from django.db.models.functions import Lower


class AdministradorUsuarios(UserManager):
    def _create_user(self, username, email, password, **extra_fields):
        return super()._create_user(
            username.strip().lower(),
            (email or "").strip().lower(),
            password,
            **extra_fields
        )

    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields.update(is_active=True, estado="aprobado")
        return super().create_superuser(username, email, password, **extra_fields)


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
                condition=models.Q(is_active=False) | models.Q(estado="aprobado"),
                name="activo_solo_aprobado",
            ),
        ]
