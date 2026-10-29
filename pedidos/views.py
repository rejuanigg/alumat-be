from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_date
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import DetallePedido, Pedido
from .serializers import Conflicto, DetallePedidoSerializer, PedidoSerializer


class PedidoViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """No ofrece DELETE: un pedido se cancela para conservar el historial."""

    serializer_class = PedidoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Pedido.objects.all()
        if self.action != "list":
            return qs
        params = self.request.query_params
        for parametro, campo in (("id_cliente", "cliente_id"), ("id_usuario", "usuario_id")):
            if params.get(parametro, "").isdigit():
                qs = qs.filter(**{campo: params[parametro]})
        if params.get("estado"):
            qs = qs.filter(estado=params["estado"])
        for parametro, filtro in (("fecha_desde", "gte"), ("fecha_hasta", "lte")):
            if params.get(parametro):
                fecha = parse_date(params[parametro])
                if fecha is None:
                    raise ValidationError({parametro: "Usá el formato AAAA-MM-DD."})
                qs = qs.filter(**{f"fecha_pedido__{filtro}": fecha})
        return qs

    def perform_create(self, serializer):
        # El responsable es siempre el usuario autenticado.
        serializer.save(usuario=self.request.user)

    @action(detail=True, methods=["post"])
    def cancelar(self, request, pk=None):
        pedido = self.get_object()
        if pedido.estado in (Pedido.Estado.CANCELADO, Pedido.Estado.ENTREGADO):
            raise Conflicto(f"Un pedido {pedido.estado} no se puede cancelar.")
        pedido.estado = Pedido.Estado.CANCELADO
        pedido.save(update_fields=["estado"])
        return Response(PedidoSerializer(pedido).data)


class DetallePedidoViewSet(viewsets.ModelViewSet):
    """Los detalles se gestionan siempre dentro de su pedido."""

    serializer_class = DetallePedidoSerializer
    permission_classes = [IsAuthenticated]

    def get_pedido(self):
        if not hasattr(self, "_pedido"):
            self._pedido = get_object_or_404(Pedido, pk=self.kwargs["id_pedido"])
        return self._pedido

    def get_queryset(self):
        return DetallePedido.objects.filter(pedido=self.get_pedido())

    def exigir_pedido_pendiente(self):
        if self.get_pedido().estado != Pedido.Estado.PENDIENTE:
            raise Conflicto("El pedido no está pendiente y no puede modificarse.")

    def perform_create(self, serializer):
        self.exigir_pedido_pendiente()
        serializer.save(pedido=self.get_pedido())

    def perform_update(self, serializer):
        self.exigir_pedido_pendiente()
        serializer.save()

    def perform_destroy(self, instance):
        self.exigir_pedido_pendiente()
        instance.delete()
