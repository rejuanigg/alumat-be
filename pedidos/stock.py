"""Stock de aberturas según el estado de los pedidos.

Reglas acordadas por el equipo:
- La unidad de stock es la abertura: se descuenta la cantidad de cada
  detalle, sin importar sus medidas.
- Se descuenta cuando el pedido deja de estar pendiente (pasa a producción,
  o directamente a terminado o entregado).
- Si el pedido se cancela, se devuelve lo descontado.
- Si no alcanza el stock de algún producto, la operación se rechaza (409) y
  el pedido no cambia de estado.

Las funciones se llaman dentro de una transacción con la fila del pedido
bloqueada (select_for_update), así dos pedidos de cambio simultáneos no
descuentan dos veces: la marca Pedido.stock_descontado se lee ya bloqueada.
"""

from django.db.models import F, Sum

from productos.models import Producto

from .models import DetallePedido, Pedido
from .serializers import Conflicto

# Estados en los que el stock del pedido tiene que estar descontado.
CONSUMEN_STOCK = (
    Pedido.Estado.EN_PRODUCCION,
    Pedido.Estado.TERMINADO,
    Pedido.Estado.ENTREGADO,
)


def cantidades_por_producto(pedido):
    filas = (
        DetallePedido.objects.filter(pedido=pedido)
        .values("producto_id")
        .annotate(total=Sum("cantidad"))
    )
    return {fila["producto_id"]: fila["total"] for fila in filas}


def descontar(pedido):
    cantidades = cantidades_por_producto(pedido)
    # Se bloquean en orden de id para evitar bloqueos cruzados entre pedidos.
    productos = Producto.objects.select_for_update().filter(pk__in=cantidades).order_by("pk")
    faltantes = [
        f"{p.nombre}: hay {p.stock}, se necesitan {cantidades[p.pk]}"
        for p in productos
        if p.stock < cantidades[p.pk]
    ]
    if faltantes:
        raise Conflicto("No hay stock suficiente. " + "; ".join(faltantes) + ".")
    for producto_id, cantidad in cantidades.items():
        Producto.objects.filter(pk=producto_id).update(stock=F("stock") - cantidad)


def devolver(pedido):
    cantidades = cantidades_por_producto(pedido)
    for producto_id in sorted(cantidades):
        Producto.objects.filter(pk=producto_id).update(
            stock=F("stock") + cantidades[producto_id]
        )


def sincronizar_stock(pedido):
    """Deja el stock acorde al estado del pedido. Se puede llamar varias veces."""
    debe_estar_descontado = pedido.estado in CONSUMEN_STOCK
    if debe_estar_descontado == pedido.stock_descontado:
        return
    if debe_estar_descontado:
        descontar(pedido)
    else:
        devolver(pedido)
    pedido.stock_descontado = debe_estar_descontado
    pedido.save(update_fields=["stock_descontado"])
