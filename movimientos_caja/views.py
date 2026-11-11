from django.db import IntegrityError, transaction
from rest_framework import viewsets
from rest_framework.exceptions import APIException
from rest_framework.permissions import IsAuthenticated
from .models import MovimientoCaja, CierreCaja
from .serializers import MovimientoCajaSerializer, CierreCajaSerializer


class Conflicto(APIException):
    status_code = 409
    default_detail = "Otro registro se guardó con los mismos datos. Revisá e intentá de nuevo."
    default_code = "conflicto"


def guardar(serializer, **datos):
    # Si dos personas guardan lo mismo a la vez, la base de datos rechaza
    # el segundo por sus índices únicos.
    try:
        with transaction.atomic():
            serializer.save(**datos)
    except IntegrityError:
        raise Conflicto()


class MovimientoCajaViewSet(viewsets.ModelViewSet):
    queryset = MovimientoCaja.objects.all()
    serializer_class = MovimientoCajaSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        guardar(serializer, id_usuario=self.request.user)

    def perform_update(self, serializer):
        guardar(serializer)


class CierreCajaViewSet(viewsets.ModelViewSet):
    queryset = CierreCaja.objects.all()
    serializer_class = CierreCajaSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        guardar(serializer, id_usuario=self.request.user)

    def perform_update(self, serializer):
        guardar(serializer)
