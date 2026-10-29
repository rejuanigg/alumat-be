from rest_framework.routers import SimpleRouter
from .views import AperturaCajaViewSet, CajaViewSet

router = SimpleRouter()
router.register(r"cajas", CajaViewSet, basename="caja")
router.register(r"aperturas", AperturaCajaViewSet, basename="apertura-caja")

urlpatterns = router.urls
