# movimientos_caja/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import MovimientoCajaViewSet, CierreCajaViewSet

router = DefaultRouter()
router.register(r"movimiento-caja", MovimientoCajaViewSet, basename='movimientos_caja')
router.register(r"cierre-caja", CierreCajaViewSet, basename='cierre_caja')

urlpatterns = [
    path("", include(router.urls))
]