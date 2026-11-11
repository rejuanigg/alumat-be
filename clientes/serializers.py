import re
from rest_framework import serializers
from .models import Cliente


def solo_digitos(valor):
    return re.sub(r"\D", "", valor or "")


def cuit_valido(digitos):
    # Dígito verificador del CUIT/CUIL (módulo 11).
    pesos = (5, 4, 3, 2, 7, 6, 5, 4, 3, 2)
    resto = sum(int(d) * p for d, p in zip(digitos[:10], pesos)) % 11
    verificador = 0 if resto == 0 else 11 - resto
    return verificador != 10 and verificador == int(digitos[10])


class ClienteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cliente
        fields = "__all__"
        read_only_fields = ("id_cliente", "fecha_registro")
        # Los repetidos de DNI y CUIT se controlan abajo con un mensaje claro.
        validators = []

    def get_extra_kwargs(self):
        extra = super().get_extra_kwargs()
        # Sin esto DRF genera un validador genérico para los índices únicos.
        for campo in ("dni", "cuit"):
            extra.setdefault(campo, {})["validators"] = []
        return extra

    def validate_dni(self, dni):
        if not dni:
            return dni
        digitos = solo_digitos(dni)
        if not 7 <= len(digitos) <= 8 or digitos != dni.replace(".", ""):
            raise serializers.ValidationError(
                "El DNI debe tener 7 u 8 números (se aceptan puntos)."
            )
        return digitos

    def validate_cuit(self, cuit):
        if not cuit:
            return cuit
        digitos = solo_digitos(cuit)
        if len(digitos) != 11 or digitos != cuit.replace("-", ""):
            raise serializers.ValidationError(
                "El CUIT debe tener 11 números (se aceptan guiones)."
            )
        if not cuit_valido(digitos):
            raise serializers.ValidationError("El CUIT no es válido.")
        return f"{digitos[:2]}-{digitos[2:10]}-{digitos[10]}"

    def validate_telefono(self, telefono):
        if not re.fullmatch(r"\+?[\d\s()-]+", telefono) or len(solo_digitos(telefono)) < 6:
            raise serializers.ValidationError(
                "Ingresá un teléfono válido (números, espacios, guiones o +)."
            )
        return telefono

    def validate_correo_electronico(self, correo):
        return correo.lower()

    def validate(self, attrs):
        def valor(campo):
            return attrs.get(campo, getattr(self.instance, campo, ""))

        tipo = valor("tipo_cliente")
        if tipo == Cliente.TipoCliente.PARTICULAR:
            obligatorios = {
                "nombre": "El nombre es obligatorio.",
                "apellido": "El apellido es obligatorio.",
                "dni": "El DNI es obligatorio.",
            }
        else:
            obligatorios = {
                "razon_social": "La razón social es obligatoria.",
                "cuit": "El CUIT es obligatorio.",
            }
        errores = {
            campo: mensaje for campo, mensaje in obligatorios.items() if not valor(campo)
        }
        if errores:
            raise serializers.ValidationError(errores)

        otros = Cliente.objects.all()
        if self.instance is not None:
            otros = otros.exclude(pk=self.instance.pk)
        for campo, mensaje in (
            ("dni", "Ya existe un cliente con ese DNI."),
            ("cuit", "Ya existe un cliente con ese CUIT."),
        ):
            if valor(campo) and otros.filter(**{campo: valor(campo)}).exists():
                errores[campo] = mensaje
        if errores:
            raise serializers.ValidationError(errores)
        return attrs
