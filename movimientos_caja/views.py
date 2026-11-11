from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from rest_framework import mixins, viewsets
from rest_framework.permissions import IsAuthenticated

from .models import CierreCaja, MovimientoCaja
from .serializers import (
    CierreCajaSerializer,
    Conflicto,
    MovimientoCajaSerializer,
    error_de_api,
)


class SoloRegistrarYConsultar(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """Sin PUT, PATCH ni DELETE: los movimientos y cierres son historial de caja."""

    permission_classes = [IsAuthenticated]
    mensaje_conflicto = "La operación no está permitida en el estado actual."

    def perform_create(self, serializer):
        try:
            with transaction.atomic():
                # El responsable es siempre el usuario autenticado.
                serializer.save(usuario=self.request.user)
        except IntegrityError:
            # Otro pedido igual se registró al mismo tiempo.
            raise Conflicto(self.mensaje_conflicto)
        except DjangoValidationError as error:
            # La apertura cambió de estado entre la validación y el guardado.
            raise error_de_api(error)


class MovimientoCajaViewSet(SoloRegistrarYConsultar):
    queryset = MovimientoCaja.objects.all()
    serializer_class = MovimientoCajaSerializer


class CierreCajaViewSet(mixins.UpdateModelMixin, SoloRegistrarYConsultar):
    """Un cierre admite corregir el efectivo contado; no se borra."""

    queryset = CierreCaja.objects.all()
    serializer_class = CierreCajaSerializer
    mensaje_conflicto = "La apertura ya está cerrada."
