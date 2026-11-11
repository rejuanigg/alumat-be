from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import APIException
from clientes.models import Cliente
from productos.models import Diseno, Producto
from .models import DetallePedido, Pedido

# Orden en que avanza un pedido. "cancelado" tiene su propio endpoint.
AVANCE = [
    Pedido.Estado.PENDIENTE,
    Pedido.Estado.EN_PRODUCCION,
    Pedido.Estado.TERMINADO,
    Pedido.Estado.ENTREGADO,
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
        if fecha > timezone.localdate():
            raise serializers.ValidationError(
                "La fecha del pedido no puede ser posterior a hoy."
            )
        return fecha

    def validate_estado(self, estado):
        if estado == Pedido.Estado.CANCELADO:
            raise serializers.ValidationError(
                "Para cancelar usá POST /api/pedidos/{id_pedido}/cancelar/."
            )
        return estado

    def validate(self, attrs):
        if self.instance is None:
            # Todo pedido nace pendiente.
            attrs.pop("estado", None)
            return attrs
        actual = self.instance.estado
        nuevo = attrs.get("estado", actual)
        if actual in (Pedido.Estado.CANCELADO, Pedido.Estado.ENTREGADO):
            raise Conflicto(f"Un pedido {actual} no admite cambios.")
        if AVANCE.index(nuevo) < AVANCE.index(actual):
            raise serializers.ValidationError(
                {"estado": "El estado de un pedido no puede retroceder."}
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
    id_producto = serializers.PrimaryKeyRelatedField(
        source="producto",
        queryset=Producto.objects.all(),
        error_messages={"does_not_exist": "El producto indicado no existe."},
    )
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
            "id_producto",
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

        producto = valor("producto")
        diseno = valor("diseno")
        if producto and diseno and diseno.producto_id != producto.pk:
            raise serializers.ValidationError(
                {"id_diseno": "El diseño elegido no corresponde al producto."}
            )
        # Un producto o diseño desactivado no se puede agregar a un pedido.
        errores = {}
        if "producto" in attrs and not producto.activo and (
            self.instance is None or producto != self.instance.producto
        ):
            errores["id_producto"] = "El producto está inactivo."
        if "diseno" in attrs and not diseno.activo and (
            self.instance is None or diseno != self.instance.diseno
        ):
            errores["id_diseno"] = "El diseño está inactivo."
        if errores:
            raise serializers.ValidationError(errores)

        # Dos renglones idénticos en el mismo pedido se cargan como uno solo
        # con más cantidad.
        pedido = self.context.get("pedido") or getattr(self.instance, "pedido", None)
        if pedido is not None:
            iguales = DetallePedido.objects.filter(
                pedido=pedido,
                producto=producto,
                diseno=diseno,
                ancho=valor("ancho"),
                alto=valor("alto"),
                tipo_vidrio__iexact=valor("tipo_vidrio"),
                color_aluminio__iexact=valor("color_aluminio"),
                tipo_revestimiento__iexact=valor("tipo_revestimiento"),
            )
            if self.instance is not None:
                iguales = iguales.exclude(pk=self.instance.pk)
            if iguales.exists():
                raise serializers.ValidationError(
                    "El pedido ya tiene un detalle igual. Modificá su cantidad."
                )
        return attrs
