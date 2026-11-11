import copy

from django.core.exceptions import NON_FIELD_ERRORS
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from rest_framework.settings import api_settings

from .models import Cliente


class ClienteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cliente
        fields = "__all__"
        read_only_fields = ("id_cliente", "fecha_registro")

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
