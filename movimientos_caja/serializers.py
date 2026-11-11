# movimientos_caja/serializers.py
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from cajas.models import AperturaCaja
from .models import MovimientoCaja, CierreCaja, TipoMovimiento


def validar_apertura_abierta(apertura):
    if apertura.estado != AperturaCaja.Estado.ABIERTA:
        raise serializers.ValidationError(
            {"id_apertura": "La apertura está cerrada y no admite movimientos."}
        )
    if CierreCaja.objects.filter(id_apertura=apertura).exists():
        raise serializers.ValidationError(
            {"id_apertura": "La apertura ya tiene un cierre registrado."}
        )


class MovimientoCajaSerializer(serializers.ModelSerializer):
    class Meta:
        model = MovimientoCaja
        fields = '__all__'
        # Evitamos que pidan el usuario en la petición, ya que lo agregas en la vista
        read_only_fields = ['id_usuario', 'fecha_movimiento']
        extra_kwargs = {
            # El cobro repetido se controla en validate() con un mensaje claro.
            'id_cobro': {'validators': []},
        }

    def validate_monto(self, monto):
        if monto <= 0:
            raise serializers.ValidationError("El monto debe ser mayor a 0.")
        return monto

    def validate(self, attrs):
        def valor(campo):
            return attrs.get(campo, getattr(self.instance, campo, None))

        # Tanto el movimiento que se carga como el que se edita tienen que
        # pertenecer a una apertura que siga abierta.
        if self.instance is not None:
            validar_apertura_abierta(self.instance.id_apertura)
        validar_apertura_abierta(valor('id_apertura'))

        cobro = valor('id_cobro')
        if cobro is not None:
            if valor('tipo_movimiento') != TipoMovimiento.ENTRADA:
                raise serializers.ValidationError(
                    {"tipo_movimiento": "Un movimiento de un cobro debe ser una entrada."}
                )
            repetidos = MovimientoCaja.objects.filter(id_cobro=cobro)
            if self.instance is not None:
                repetidos = repetidos.exclude(pk=self.instance.pk)
            if repetidos.exists():
                raise serializers.ValidationError(
                    {"id_cobro": "Ese cobro ya tiene un movimiento de caja."}
                )

        # Reutiliza la regla del modelo sobre transferencias y tarjetas.
        try:
            MovimientoCaja(
                **{k: v for k, v in attrs.items() if k != 'id_cobro'},
                id_cobro=cobro,
            ).clean()
        except DjangoValidationError as error:
            raise serializers.ValidationError({"id_cobro": error.messages})
        return attrs


class CierreCajaSerializer(serializers.ModelSerializer):
    class Meta:
        model = CierreCaja
        fields = '__all__'
        read_only_fields = ['id_usuario', 'fecha_hora_cierre', 'total_ingresos', 'total_egresos', 'saldo_esperado', 'diferencia']
        extra_kwargs = {
            # El cierre repetido se controla abajo con un mensaje claro.
            'id_apertura': {'validators': []},
        }

    def validate_id_apertura(self, apertura):
        if self.instance is not None:
            if apertura != self.instance.id_apertura:
                raise serializers.ValidationError(
                    "La apertura de un cierre no se puede modificar."
                )
            return apertura
        if apertura.estado != AperturaCaja.Estado.ABIERTA:
            raise serializers.ValidationError("La apertura ya está cerrada.")
        if CierreCaja.objects.filter(id_apertura=apertura).exists():
            raise serializers.ValidationError(
                "La apertura ya tiene un cierre registrado."
            )
        return apertura

    def validate_efectivo_contado(self, efectivo):
        if efectivo < 0:
            raise serializers.ValidationError(
                "El efectivo contado no puede ser negativo."
            )
        return efectivo
