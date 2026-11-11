from django.core.exceptions import NON_FIELD_ERRORS
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from rest_framework.exceptions import APIException
from rest_framework.settings import api_settings

from cajas.models import AperturaCaja
from ventas.models import Cobro

from .models import CierreCaja, MovimientoCaja

# Nombre del campo en el modelo -> nombre en el JSON de la API.
NOMBRES_API = {
    "apertura": "id_apertura",
    "cobro": "id_cobro",
    "usuario": "id_usuario",
    NON_FIELD_ERRORS: api_settings.NON_FIELD_ERRORS_KEY,
}


class Conflicto(APIException):
    status_code = 409
    default_detail = "La operación no está permitida en el estado actual."
    default_code = "conflicto"


def error_de_api(error):
    """Traduce un ValidationError de Django a uno de DRF (400) con los nombres de la API."""
    return serializers.ValidationError(
        {NOMBRES_API.get(campo, campo): mensajes for campo, mensajes in error.message_dict.items()}
    )


def exigir_apertura_abierta(apertura):
    if apertura.estado != AperturaCaja.Estado.ABIERTA:
        raise Conflicto("La apertura ya está cerrada.")


class MovimientoCajaSerializer(serializers.ModelSerializer):
    id_apertura = serializers.PrimaryKeyRelatedField(
        source="apertura",
        queryset=AperturaCaja.objects.all(),
        error_messages={"does_not_exist": "La apertura indicada no existe."},
    )
    id_cobro = serializers.PrimaryKeyRelatedField(
        source="cobro",
        queryset=Cobro.objects.all(),
        required=False,
        allow_null=True,
        error_messages={"does_not_exist": "El cobro indicado no existe."},
    )
    id_usuario = serializers.PrimaryKeyRelatedField(source="usuario", read_only=True)

    class Meta:
        model = MovimientoCaja
        fields = (
            "id_movimiento",
            "id_apertura",
            "id_cobro",
            "id_usuario",
            "fecha_movimiento",
            "tipo_movimiento",
            "concepto",
            "monto",
        )
        # La fecha la pone el servidor.
        read_only_fields = ("fecha_movimiento",)
        # El cobro repetido se informa en validate() con un mensaje claro.
        validators = []

    def validate(self, attrs):
        exigir_apertura_abierta(attrs["apertura"])
        cobro = attrs.get("cobro")
        if cobro is not None and MovimientoCaja.objects.filter(cobro=cobro).exists():
            raise serializers.ValidationError(
                {"id_cobro": "Ese cobro ya tiene un movimiento de caja."}
            )
        # Reutiliza las reglas del modelo (cobro en efectivo, cobro = entrada).
        try:
            MovimientoCaja(**attrs).clean()
        except DjangoValidationError as error:
            raise error_de_api(error)
        return attrs


class CierreCajaSerializer(serializers.ModelSerializer):
    id_apertura = serializers.PrimaryKeyRelatedField(
        source="apertura",
        queryset=AperturaCaja.objects.all(),
        error_messages={"does_not_exist": "La apertura indicada no existe."},
    )
    id_usuario = serializers.PrimaryKeyRelatedField(source="usuario", read_only=True)

    class Meta:
        model = CierreCaja
        fields = (
            "id_cierre",
            "id_apertura",
            "id_usuario",
            "fecha_hora_cierre",
            "total_ingresos",
            "total_egresos",
            "saldo_esperado",
            "efectivo_contado",
            "diferencia",
        )
        # Todo lo calcula el servidor; solo se envían la apertura y el efectivo contado.
        read_only_fields = (
            "fecha_hora_cierre",
            "total_ingresos",
            "total_egresos",
            "saldo_esperado",
            "diferencia",
        )
        # "Un cierre por apertura" se informa con 409 en validate(); la base lo
        # sigue garantizando con su restricción única.
        validators = []

    def validate(self, attrs):
        if self.instance is None:
            exigir_apertura_abierta(attrs["apertura"])
        elif attrs.get("apertura", self.instance.apertura) != self.instance.apertura:
            raise serializers.ValidationError(
                {"id_apertura": "La apertura de un cierre no se puede modificar."}
            )
        return attrs
