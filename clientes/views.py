from django.db import IntegrityError, transaction
from rest_framework import mixins, viewsets
from rest_framework.exceptions import APIException
from rest_framework.permissions import IsAuthenticated

from .models import Cliente
from .serializers import ClienteSerializer


class Conflicto(APIException):
    status_code = 409
    default_detail = "Otro cliente se guardó con el mismo DNI o CUIT. Revisá e intentá de nuevo."
    default_code = "conflicto"


class ClienteViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """No ofrece DELETE: un cliente se desactiva (activo=false) para conservar sus pedidos."""

    serializer_class = ClienteSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Cliente.objects.all()
        if self.action != "list":
            return qs

        params = self.request.query_params

        activo = params.get("activo", "").lower()
        if activo in ("true", "false"):
            qs = qs.filter(activo=activo == "true")

        tipo = params.get("tipo_cliente")
        if tipo in Cliente.TipoCliente.values:
            qs = qs.filter(tipo_cliente=tipo)

        return qs

    def guardar(self, serializer):
        try:
            with transaction.atomic():
                serializer.save()
        except IntegrityError:
            # Otro cliente con el mismo DNI o CUIT se guardó al mismo tiempo.
            raise Conflicto()

    def perform_create(self, serializer):
        self.guardar(serializer)

    def perform_update(self, serializer):
        self.guardar(serializer)
