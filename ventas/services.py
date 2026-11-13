from django.core.exceptions import ValidationError
from django.db import transaction

from cajas.models import AperturaCaja
from movimientos_caja.models import MovimientoCaja, TipoMovimiento

from .models import Cobro, MetodoPago, Venta


@transaction.atomic
def registrar_cobro(*, venta, usuario, monto, tipo_cobro, metodo_pago, numero_boleta, apertura=None):
    """Registra un cobro. Si es en efectivo, exige una apertura abierta y
    registra automáticamente el movimiento de Entrada en esa caja."""
    venta = Venta.objects.select_for_update().get(pk=venta.pk)  # evita cobrar dos veces el mismo saldo
    cobro = Cobro(venta=venta, usuario=usuario, monto=monto, tipo_cobro=tipo_cobro,
                  metodo_pago=metodo_pago, numero_boleta=numero_boleta)
    cobro.full_clean()
    if metodo_pago == MetodoPago.EFECTIVO:
        if apertura is None:
            raise ValidationError({"apertura": "Para cobrar en efectivo tiene que haber una caja abierta."})
        apertura = AperturaCaja.objects.select_for_update().get(pk=apertura.pk)
        if apertura.estado != AperturaCaja.Estado.ABIERTA:
            raise ValidationError({"apertura": "La caja de esta apertura ya está cerrada."})
    cobro.save()
    if metodo_pago == MetodoPago.EFECTIVO:
        MovimientoCaja.objects.create(
            apertura=apertura, cobro=cobro, usuario=usuario,
            tipo_movimiento=TipoMovimiento.ENTRADA,
            concepto=f"Cobro boleta {numero_boleta}", monto=monto,
        )
    return cobro
