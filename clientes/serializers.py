import copy
import re

from django.core.exceptions import NON_FIELD_ERRORS
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from rest_framework.settings import api_settings

from .models import Cliente, cuit_valido, solo_digitos


class ClienteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cliente
        fields = "__all__"
        read_only_fields = ("id_cliente", "fecha_registro")

    def validate_dni(self, dni):
        dni = solo_digitos(dni)
        if dni and not re.fullmatch(r"\d{7,8}", dni):
            raise serializers.ValidationError("El DNI debe tener 7 u 8 dígitos.")
        return dni

    def validate_cuit(self, cuit):
        cuit = solo_digitos(cuit)
        if cuit and not re.fullmatch(r"\d{11}", cuit):
            raise serializers.ValidationError("El CUIT debe tener 11 dígitos.")
        if cuit and not cuit_valido(cuit):
            raise serializers.ValidationError("El CUIT no es válido (dígito verificador).")
        return cuit

    def validate_telefono(self, telefono):
        telefono = telefono.strip()
        if not re.fullmatch(r"\+?[\d\s()-]+", telefono) or len(re.sub(r"\D", "", telefono)) < 6:
            raise serializers.ValidationError(
                "Ingresá un teléfono válido (números, espacios, guiones o +)."
            )
        return telefono

    def validate_correo_electronico(self, correo):
        return correo.strip().lower()

    def validate(self, attrs):
        # DRF no llama a Model.clean(): se arma el cliente como quedaría
        # (en un PATCH, mezclando con los datos actuales) y se valida entero.
        cliente = copy.copy(self.instance) if self.instance else Cliente()
        for campo, valor in attrs.items():
            setattr(cliente, campo, valor)

        try:
            cliente.full_clean()
        except DjangoValidationError as error:
            raise serializers.ValidationError(
                {
                    api_settings.NON_FIELD_ERRORS_KEY if campo == NON_FIELD_ERRORS else campo: mensajes
                    for campo, mensajes in error.message_dict.items()
                }
            )

        # clean() normaliza (espacios, DNI/CUIT solo dígitos): se guardan esos valores.
        for campo in Cliente.CAMPOS_PARTICULAR + Cliente.CAMPOS_EMPRESA:
            attrs[campo] = getattr(cliente, campo)

        return attrs
