from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import APIException
from clientes.models import Cliente
from productos.models import Diseno
from .models import DetallePedido, Pedido

# Orden en que avanza un pedido (E026): solo hacia adelante y de a un paso.
AVANCE = [
    Pedido.Estado.PENDIENTE,
    Pedido.Estado.EN_PROCESO,
    Pedido.Estado.FINALIZADO,
]


class Conflicto(APIException):
    status_code = 409
    default_detail = "La operación no está permitida en el estado actual."
    default_code = "conflicto"


class PedidoSerializer(serializers.ModelSerializer):
    id_cliente = serializers.PrimaryKeyRelatedField(
        source="cliente",
        queryset=Cliente.objects.all(),
        error_messages={"does_not_exist": "El cliente indicado no existe."},
    )
    id_usuario = serializers.PrimaryKeyRelatedField(source="usuario", read_only=True)

    class Meta:
        model = Pedido
        fields = (
            "id_pedido",
            "id_cliente",
            "id_usuario",
            "fecha_pedido",
            "estado",
            "observaciones",
        )

    def validate_id_cliente(self, cliente):
        cambia = self.instance is None or cliente != self.instance.cliente
        if cambia and not cliente.activo:
            raise serializers.ValidationError(
                "No se puede asignar un pedido a un cliente inactivo."
            )
        return cliente

    def validate_fecha_pedido(self, fecha):
        if fecha > timezone.now():
            raise serializers.ValidationError(
                "La fecha del pedido no puede ser posterior a este momento."
            )
        return fecha

    def validate(self, attrs):
        if self.instance is None:
            # Todo pedido nace pendiente.
            attrs.pop("estado", None)
            return attrs
        actual = self.instance.estado
        nuevo = attrs.get("estado", actual)
        if actual == Pedido.Estado.FINALIZADO:
            raise Conflicto("Un pedido finalizado no admite cambios.")
        paso = AVANCE.index(nuevo) - AVANCE.index(actual)
        if paso < 0:
            raise serializers.ValidationError(
                {"estado": "El estado de un pedido no puede retroceder."}
            )
        if paso > 1:
            raise serializers.ValidationError(
                {"estado": "El estado avanza de a un paso: pendiente → en proceso → finalizado."}
            )
        otros_cambios = any(
            getattr(self.instance, campo) != valor
            for campo, valor in attrs.items()
            if campo != "estado"
        )
        if actual != Pedido.Estado.PENDIENTE and otros_cambios:
            raise Conflicto(
                "El pedido no está pendiente: solo se puede avanzar su estado."
            )
        return attrs


class DetallePedidoSerializer(serializers.ModelSerializer):
    id_pedido = serializers.PrimaryKeyRelatedField(source="pedido", read_only=True)
    id_diseno = serializers.PrimaryKeyRelatedField(
        source="diseno",
        queryset=Diseno.objects.all(),
        error_messages={"does_not_exist": "El diseño indicado no existe."},
    )

    class Meta:
        model = DetallePedido
        fields = (
            "id_detalle_pedido",
            "id_pedido",
            "id_diseno",
            "ancho",
            "alto",
            "cantidad",
            "tipo_vidrio",
            "color_aluminio",
            "tipo_revestimiento",
            "observaciones",
        )

    def validate(self, attrs):
        def valor(campo):
            return attrs.get(campo, getattr(self.instance, campo, None))

        diseno = valor("diseno")
        # Un diseño desactivado, o de un producto desactivado, no se puede
        # agregar a un pedido. El producto se obtiene a través del diseño.
        if "diseno" in attrs and (self.instance is None or diseno != self.instance.diseno):
            if not diseno.activo:
                raise serializers.ValidationError({"id_diseno": "El diseño está inactivo."})
            if not diseno.producto.activo:
                raise serializers.ValidationError(
                    {"id_diseno": "El producto de este diseño está inactivo."}
                )

        # Dos renglones idénticos en el mismo pedido se cargan como uno solo
        # con más cantidad.
        pedido = self.context.get("pedido") or getattr(self.instance, "pedido", None)
        if pedido is not None:
            iguales = DetallePedido.objects.filter(
                pedido=pedido,
                diseno=diseno,
                ancho=valor("ancho"),
                alto=valor("alto"),
                tipo_vidrio=valor("tipo_vidrio") or "",
                color_aluminio=valor("color_aluminio"),
                tipo_revestimiento=valor("tipo_revestimiento") or "",
            )
            if self.instance is not None:
                iguales = iguales.exclude(pk=self.instance.pk)
            if iguales.exists():
                raise serializers.ValidationError(
                    "El pedido ya tiene un detalle igual. Modificá su cantidad."
                )
        return attrs
