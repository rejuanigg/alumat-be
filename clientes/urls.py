from rest_framework.routers import SimpleRouter

from .views import ClienteViewSet

# SimpleRouter: no agrega su propia raíz en /api/ (la comparten varias apps).
router = SimpleRouter()
router.register(r"clientes", ClienteViewSet, basename="cliente")

urlpatterns = router.urls
