from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from .models import AperturaCaja, Caja


class CajaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Caja
        fields = ("id_caja", "nombre_caja", "activa")

    def validate_nombre_caja(self, nombre):
        repetidas = Caja.objects.filter(nombre_caja__iexact=nombre)
        if self.instance is not None:
            repetidas = repetidas.exclude(pk=self.instance.pk)
        if repetidas.exists():
            raise serializers.ValidationError("Ya existe una caja con ese nombre.")
        return nombre


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
        # La fecha y hora la pone el servidor; el estado cambia con POST /api/cierre-caja/.
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
