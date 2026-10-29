
from django.db import models
from django.core.exceptions import ValidationError


class Cliente(models.Model):

    class TipoCliente(models.TextChoices):
        PARTICULAR = "particular", "Particular"
        EMPRESA = "empresa", "Empresa"

    id_cliente = models.AutoField(primary_key=True)

    tipo_cliente = models.CharField(
        max_length=20,
        choices=TipoCliente.choices
    )

    nombre = models.CharField(
        max_length=100,
        blank=True
    )

    apellido = models.CharField(
        max_length=100,
        blank=True
    )

    dni = models.CharField(
        max_length=20,
        blank=True
    )

    razon_social = models.CharField(
        max_length=150,
        blank=True
    )

    cuit = models.CharField(
        max_length=13,
        blank=True
    )

    direccion = models.CharField(max_length=200)

    telefono = models.CharField(max_length=30)

    correo_electronico = models.EmailField(
        max_length=150
    )

    activo = models.BooleanField(default=True)

    fecha_registro = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        if self.tipo_cliente == self.TipoCliente.EMPRESA:
            return self.razon_social

        return f"{self.nombre} {self.apellido}"

    def clean(self):
        super().clean()

        errores = {}

        if self.tipo_cliente == self.TipoCliente.PARTICULAR:

            if not self.nombre or not self.nombre.strip():
                errores["nombre"] = "El nombre es obligatorio."

            if not self.apellido or not self.apellido.strip():
                errores["apellido"] = "El apellido es obligatorio."

            if not self.dni or not self.dni.strip():
                errores["dni"] = "El DNI es obligatorio."

        elif self.tipo_cliente == self.TipoCliente.EMPRESA:

            if not self.razon_social or not self.razon_social.strip():
                errores["razon_social"] = "La razón social es obligatoria."

            if not self.cuit or not self.cuit.strip():
                errores["cuit"] = "El CUIT es obligatorio."

        if errores:
            raise ValidationError(errores)
