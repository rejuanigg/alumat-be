from rest_framework.routers import SimpleRouter
from .views import DisenoViewSet, ProductoViewSet

router = SimpleRouter()
router.register(r"productos", ProductoViewSet, basename="producto")
router.register(r"disenos", DisenoViewSet, basename="diseno")

urlpatterns = router.urls
