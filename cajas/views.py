from django.db import IntegrityError, transaction
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import APIException
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import AperturaCaja, Caja
from .serializers import AperturaCajaSerializer, CajaSerializer


class Conflicto(APIException):
    status_code = 409
    default_detail = "La operación no está permitida en el estado actual."
    default_code = "conflicto"


class CajaViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """No ofrece DELETE: una caja se desactiva para conservar su historial."""

    serializer_class = CajaSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Caja.objects.all()
        valor = self.request.query_params.get("activa", "").lower()
        if self.action == "list" and valor in ("true", "false"):
            qs = qs.filter(activa=valor == "true")
        return qs

    def perform_create(self, serializer):
        try:
            with transaction.atomic():
                serializer.save()
        except IntegrityError:
            raise Conflicto("Ya existe una caja con ese nombre.")

    def perform_update(self, serializer):
        try:
            with transaction.atomic():
                serializer.save()
        except IntegrityError:
            raise Conflicto("Ya existe una caja con ese nombre.")

    @action(detail=True, methods=["get"])
    def aperturas(self, request, pk=None):
        caja = self.get_object()
        return Response(AperturaCajaSerializer(caja.aperturas.all(), many=True).data)


class AperturaCajaViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """Una apertura no se modifica ni se borra: se registra aquí y se cierra
    únicamente con POST /api/cierre-caja/, que registra el efectivo contado."""

    serializer_class = AperturaCajaSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = AperturaCaja.objects.all()
        if self.action != "list":
            return qs
        params = self.request.query_params
        for parametro, campo in (("id_caja", "caja_id"), ("id_usuario", "usuario_id")):
            if params.get(parametro, "").isdigit():
                qs = qs.filter(**{campo: params[parametro]})
        if params.get("estado"):
            qs = qs.filter(estado=params["estado"])
        return qs

    def perform_create(self, serializer):
        try:
            with transaction.atomic():
                # El responsable es siempre el usuario autenticado.
                serializer.save(usuario=self.request.user)
        except IntegrityError:
            # Otra apertura de la misma caja se registró al mismo tiempo.
            raise Conflicto("La caja ya tiene una apertura abierta.")
