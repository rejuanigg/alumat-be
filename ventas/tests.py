from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from cajas.models import AperturaCaja, Caja
from clientes.models import Cliente
from movimientos_caja.models import MovimientoCaja, TipoMovimiento
from pedidos.models import Pedido

from .models import Cobro, MetodoPago, TipoCobro, Venta
from .services import registrar_cobro


class VentaYCobroTests(TestCase):
    def setUp(self):
        self.usuario = get_user_model().objects.create_user(
            "vendedora", "vendedora@example.test", "clave-de-prueba-123"
        )
        cliente = Cliente.objects.create(
            tipo_cliente="particular", nombre="Ana", apellido="Pérez", dni="30123456"
        )
        self.pedido = Pedido.objects.create(cliente=cliente, usuario=self.usuario)
        self.venta = Venta.objects.create(
            pedido=self.pedido, usuario=self.usuario, importe_total=Decimal("1000")
        )
        self.apertura = AperturaCaja.objects.create(
            caja=Caja.objects.create(nombre_caja="Principal"),
            usuario=self.usuario,
            monto_inicial=Decimal("0"),
        )

    def cobrar(self, monto, tipo=TipoCobro.PARCIAL, metodo=MetodoPago.TRANSFERENCIA,
               boleta="B-1", apertura=None):
        return registrar_cobro(
            venta=self.venta, usuario=self.usuario, monto=Decimal(monto),
            tipo_cobro=tipo, metodo_pago=metodo, numero_boleta=boleta, apertura=apertura,
        )

    def test_venta_con_importe_cero_se_rechaza(self):
        venta = Venta(pedido=self.pedido, usuario=self.usuario, importe_total=Decimal("0"))
        with self.assertRaises(ValidationError) as error:
            venta.full_clean(exclude=["pedido"])
        self.assertIn("importe_total", error.exception.message_dict)
        # La base de datos también lo impide.
        with self.assertRaises(IntegrityError), transaction.atomic():
            Venta.objects.filter(pk=self.venta.pk).update(importe_total=0)

    def test_un_pedido_no_tiene_dos_ventas(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Venta.objects.create(
                pedido=self.pedido, usuario=self.usuario, importe_total=Decimal("10")
            )

    def test_saldo_pendiente(self):
        self.cobrar("300")
        self.assertEqual(self.venta.total_cobrado, Decimal("300"))
        self.assertEqual(self.venta.saldo_pendiente, Decimal("700"))

    def test_cobro_mayor_al_saldo_se_rechaza(self):
        self.cobrar("600")
        with self.assertRaises(ValidationError) as error:
            self.cobrar("500", boleta="B-2")
        self.assertIn("monto", error.exception.message_dict)
        self.assertEqual(Cobro.objects.count(), 1)

    def test_cobro_total_con_saldo_exacto_se_acepta(self):
        self.cobrar("400")
        cobro = self.cobrar("600", tipo=TipoCobro.TOTAL, boleta="B-2")
        self.assertEqual(cobro.tipo_cobro, TipoCobro.TOTAL)
        self.assertEqual(self.venta.saldo_pendiente, Decimal("0"))

    def test_cobro_total_que_no_cubre_el_saldo_se_rechaza(self):
        with self.assertRaises(ValidationError) as error:
            self.cobrar("100", tipo=TipoCobro.TOTAL)
        self.assertIn("tipo_cobro", error.exception.message_dict)

    def test_cobro_parcial_que_cubre_el_saldo_se_rechaza(self):
        with self.assertRaises(ValidationError) as error:
            self.cobrar("1000", tipo=TipoCobro.PARCIAL)
        self.assertIn("tipo_cobro", error.exception.message_dict)

    def test_numero_de_boleta_repetido_se_rechaza(self):
        self.cobrar("100", boleta="B-9")
        with self.assertRaises(ValidationError) as error:
            self.cobrar("100", boleta="B-9")
        self.assertEqual(
            error.exception.message_dict["numero_boleta"],
            ["Ese número de boleta ya fue registrado."],
        )

    def test_efectivo_sin_apertura_se_rechaza(self):
        with self.assertRaises(ValidationError) as error:
            self.cobrar("100", metodo=MetodoPago.EFECTIVO)
        self.assertIn("apertura", error.exception.message_dict)
        self.assertFalse(Cobro.objects.exists())

    def test_efectivo_con_apertura_cerrada_se_rechaza(self):
        AperturaCaja.objects.filter(pk=self.apertura.pk).update(estado="cerrada")
        with self.assertRaises(ValidationError):
            self.cobrar("100", metodo=MetodoPago.EFECTIVO, apertura=self.apertura)
        self.assertFalse(Cobro.objects.exists())

    def test_efectivo_con_apertura_abierta_crea_la_entrada(self):
        cobro = self.cobrar("250", metodo=MetodoPago.EFECTIVO, apertura=self.apertura)
        movimiento = MovimientoCaja.objects.get()
        self.assertEqual(movimiento.cobro, cobro)
        self.assertEqual(movimiento.apertura, self.apertura)
        self.assertEqual(movimiento.tipo_movimiento, TipoMovimiento.ENTRADA)
        self.assertEqual(movimiento.monto, Decimal("250"))
        self.assertEqual(movimiento.usuario, self.usuario)

    def test_transferencia_no_crea_movimiento(self):
        self.cobrar("250", metodo=MetodoPago.TRANSFERENCIA, apertura=self.apertura)
        self.assertFalse(MovimientoCaja.objects.exists())

    def test_etiqueta_de_transferencia(self):
        self.assertEqual(MetodoPago.TRANSFERENCIA.label, "Transferencia bancaria")
        self.assertEqual(MetodoPago.TRANSFERENCIA.value, "transferencia")

    def test_tablas_del_der(self):
        self.assertEqual(Venta._meta.db_table, "ventas")
        self.assertEqual(Cobro._meta.db_table, "cobros")
