from rest_framework.routers import SimpleRouter
from .views import DetallePedidoViewSet, PedidoViewSet

router = SimpleRouter()
router.register(r"pedidos", PedidoViewSet, basename="pedido")
router.register(
    r"pedidos/(?P<id_pedido>\d+)/detalles",
    DetallePedidoViewSet,
    basename="detalle-pedido",
)

urlpatterns = router.urls
