from django.db import IntegrityError, transaction
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import APIException
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from cuentas.permisos import PermisoPorRol

from .models import Diseno, Producto
from .serializers import DisenoSerializer, ProductoSerializer


class Conflicto(APIException):
    status_code = 409
    default_detail = "Otro registro se guardó con los mismos datos. Revisá e intentá de nuevo."
    default_code = "conflicto"


def filtrar_activo(queryset, request, campo="activo"):
    valor = request.query_params.get(campo, "").lower()
    if valor in ("true", "false"):
        queryset = queryset.filter(**{campo: valor == "true"})
    return queryset


class SinBorradoViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """No ofrece DELETE: los registros se desactivan para conservar el historial."""

    permission_classes = [IsAuthenticated, PermisoPorRol]

    # El serializer avisa los repetidos con un 400 claro; si dos personas
    # guardan lo mismo a la vez, la base de datos rechaza el segundo.
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


class ProductoViewSet(SinBorradoViewSet):
    serializer_class = ProductoSerializer

    def get_queryset(self):
        qs = Producto.objects.all()
        if self.action != "list":
            return qs
        qs = filtrar_activo(qs, self.request)
        tipo = self.request.query_params.get("tipo_abertura", "").strip()
        if tipo:
            qs = qs.filter(tipo_abertura=tipo)
        q = self.request.query_params.get("q", "").strip()[:100]
        if q:
            qs = qs.filter(nombre__icontains=q)
        return qs

    @action(detail=True, methods=["get"])
    def disenos(self, request, pk=None):
        producto = self.get_object()
        disenos = filtrar_activo(producto.disenos.all(), request)
        return Response(DisenoSerializer(disenos, many=True).data)


class DisenoViewSet(SinBorradoViewSet):
    serializer_class = DisenoSerializer

    def get_queryset(self):
        qs = Diseno.objects.all()
        if self.action != "list":
            return qs
        qs = filtrar_activo(qs, self.request)
        id_producto = self.request.query_params.get("id_producto", "")
        if id_producto.isdigit():
            qs = qs.filter(producto_id=id_producto)
        return qs
