from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from .models import AperturaCaja, Caja


class CajaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Caja
        fields = ("id_caja", "nombre_caja", "activa")


class AperturaCajaSerializer(serializers.ModelSerializer):
    id_caja = serializers.PrimaryKeyRelatedField(
        source="caja",
        queryset=Caja.objects.all(),
        error_messages={"does_not_exist": "La caja indicada no existe."},
    )
    id_usuario = serializers.PrimaryKeyRelatedField(source="usuario", read_only=True)

    class Meta:
        model = AperturaCaja
        fields = (
            "id_apertura",
            "id_caja",
            "id_usuario",
            "fecha_hora_apertura",
            "monto_inicial",
            "estado",
        )
        # La fecha y hora la pone el servidor; el estado cambia con /cerrar/.
        read_only_fields = ("fecha_hora_apertura", "estado")
        # "Una apertura abierta por caja" se valida en validate() con un mensaje
        # claro; la base de datos lo sigue garantizando con su índice único.
        validators = []

    def validate(self, attrs):
        # Reutiliza las condiciones de apertura del modelo.
        try:
            AperturaCaja(**attrs).validar_condiciones()
        except DjangoValidationError as error:
            raise serializers.ValidationError(
                {
                    "id_caja" if campo == "caja" else campo: mensajes
                    for campo, mensajes in error.message_dict.items()
                }
            )
        return attrs
