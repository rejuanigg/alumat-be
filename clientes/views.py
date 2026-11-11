from django.db import IntegrityError, transaction
from rest_framework import viewsets
from rest_framework.exceptions import APIException
from .models import Cliente
from .serializers import ClienteSerializer


class Conflicto(APIException):
    status_code = 409
    default_detail = "Otro cliente se guardó con el mismo DNI o CUIT. Revisá e intentá de nuevo."
    default_code = "conflicto"


class ClienteViewSet(viewsets.ModelViewSet):
    queryset = Cliente.objects.all()
    serializer_class = ClienteSerializer

    # Si dos personas cargan el mismo DNI o CUIT a la vez, la base de datos
    # rechaza el segundo.
    def perform_create(self, serializer):
        try:
            with transaction.atomic():
                serializer.save()
        except IntegrityError:
            raise Conflicto()

    def perform_update(self, serializer):
        try:
            with transaction.atomic():
                serializer.save()
        except IntegrityError:
            raise Conflicto()
