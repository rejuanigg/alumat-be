from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import MovimientoCaja, CierreCaja
from .serializers import MovimientoCajaSerializer, CierreCajaSerializer

class MovimientoCajaViewSet(viewsets.ModelViewSet):
    queryset = MovimientoCaja.objects.all()
    serializer_class = MovimientoCajaSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(id_usuario=self.request.user)


class CierreCajaViewSet(viewsets.ModelViewSet):
    queryset = CierreCaja.objects.all()
    serializer_class = CierreCajaSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(id_usuario=self.request.user)
