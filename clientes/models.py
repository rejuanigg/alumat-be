import re

from django.core.exceptions import NON_FIELD_ERRORS, ValidationError
from django.db import models
from django.db.models import Q


def solo_digitos(valor):
    """Quita puntos, guiones y espacios: "20-12.345.678-9" -> "20123456789"."""
    return re.sub(r"[\s.\-]", "", valor or "")


def formatear_cuit(cuit):
    """"20123456786" -> "20-12345678-6" (formato XX-XXXXXXXX-X del diccionario)."""
    return f"{cuit[:2]}-{cuit[2:10]}-{cuit[10]}"


def cuit_valido(cuit):
    """Controla el dígito verificador de un CUIT/CUIL de 11 dígitos."""
    pesos = (5, 4, 3, 2, 7, 6, 5, 4, 3, 2)
    suma = sum(int(d) * p for d, p in zip(cuit[:10], pesos))
    verificador = 11 - suma % 11
    if verificador == 11:
        verificador = 0
    elif verificador == 10:
        return False
    return verificador == int(cuit[10])


class Cliente(models.Model):

    class TipoCliente(models.TextChoices):
        PARTICULAR = "particular", "Particular"
        EMPRESA = "empresa", "Empresa"

    # Campos propios de cada tipo: los del otro tipo deben quedar vacíos.
    CAMPOS_PARTICULAR = ("nombre", "apellido", "dni")
    CAMPOS_EMPRESA = ("razon_social", "cuit")

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

    # Se guarda solo con dígitos (7 u 8).
    dni = models.CharField(
        max_length=20,
        blank=True
    )

    razon_social = models.CharField(
        max_length=150,
        blank=True
    )

    # Se guarda con el formato del diccionario: XX-XXXXXXXX-X (13 caracteres).
    cuit = models.CharField(
        max_length=13,
        blank=True
    )

    # Dirección, teléfono y correo son opcionales (diccionario E008, E009, E010).
    direccion = models.CharField(max_length=200, blank=True)
    telefono = models.CharField(max_length=30, blank=True)
    correo_electronico = models.EmailField(max_length=150, blank=True)

    # Se desactiva en lugar de borrar para conservar los pedidos.
    activo = models.BooleanField(default=True)

    fecha_registro = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        db_table = "clientes"
        verbose_name = "cliente"
        verbose_name_plural = "clientes"
        ordering = ["id_cliente"]
        constraints = [
            # Vacío no cuenta como repetido: las empresas no tienen DNI.
            models.UniqueConstraint(
                fields=["dni"],
                condition=~Q(dni=""),
                name="cliente_dni_unico",
                violation_error_message="Ya existe un cliente con ese DNI.",
            ),
            models.UniqueConstraint(
                fields=["cuit"],
                condition=~Q(cuit=""),
                name="cliente_cuit_unico",
                violation_error_message="Ya existe un cliente con ese CUIT.",
            ),
        ]

    def __str__(self):
        if self.tipo_cliente == self.TipoCliente.EMPRESA:
            texto = self.razon_social
        else:
            texto = f"{self.nombre} {self.apellido}".strip()

        return texto or f"Cliente #{self.pk}"

    def validate_constraints(self, exclude=None):
        # Django informa las restricciones con condición como error general;
        # se pasan al campo (dni / cuit) para que el formulario lo marque.
        try:
            super().validate_constraints(exclude=exclude)
        except ValidationError as error:
            campo_de = {
                c.violation_error_message: c.fields[0]
                for c in self._meta.constraints
                if isinstance(c, models.UniqueConstraint) and c.fields
            }
            errores = {}
            for campo, mensajes in error.message_dict.items():
                for mensaje in mensajes:
                    destino = campo_de.get(mensaje, campo) if campo == NON_FIELD_ERRORS else campo
                    errores.setdefault(destino, []).append(mensaje)
            raise ValidationError(errores)

    def clean(self):
        super().clean()

        errores = {}

        # Se quitan espacios sobrantes antes de validar y guardar.
        for campo in self.CAMPOS_PARTICULAR + self.CAMPOS_EMPRESA:
            setattr(self, campo, (getattr(self, campo) or "").strip())

        self.dni = solo_digitos(self.dni)
        self.cuit = solo_digitos(self.cuit)

        if self.tipo_cliente == self.TipoCliente.PARTICULAR:
            obligatorios = {
                "nombre": "El nombre es obligatorio.",
                "apellido": "El apellido es obligatorio.",
                "dni": "El DNI es obligatorio.",
            }
            sobrantes = self.CAMPOS_EMPRESA

            if self.dni and not re.fullmatch(r"\d{7,8}", self.dni):
                errores["dni"] = "El DNI debe tener 7 u 8 dígitos."

        elif self.tipo_cliente == self.TipoCliente.EMPRESA:
            obligatorios = {
                "razon_social": "La razón social es obligatoria.",
                "cuit": "El CUIT es obligatorio.",
            }
            sobrantes = self.CAMPOS_PARTICULAR

            if self.cuit and not re.fullmatch(r"\d{11}", self.cuit):
                errores["cuit"] = "El CUIT debe tener 11 dígitos."
            elif self.cuit and not cuit_valido(self.cuit):
                errores["cuit"] = "El CUIT no es válido (dígito verificador)."
            elif self.cuit:
                self.cuit = formatear_cuit(self.cuit)

        else:
            # tipo_cliente inválido: ya lo informa la validación del campo.
            obligatorios, sobrantes = {}, ()

        for campo, mensaje in obligatorios.items():
            if not getattr(self, campo):
                errores[campo] = mensaje

        for campo in sobrantes:
            if getattr(self, campo):
                errores[campo] = "No corresponde para este tipo de cliente."

        if errores:
            raise ValidationError(errores)
