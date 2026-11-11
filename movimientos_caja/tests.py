from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from cajas.models import AperturaCaja, Caja
from ventas.models import Cobro, Venta

from .models import CierreCaja, MovimientoCaja, TipoMovimiento


class CajaTestCase(TestCase):
    def setUp(self):
        self.usuario = get_user_model().objects.create_user(
            "cajera", "cajera@example.test", "clave-de-prueba-123"
        )
        self.apertura = AperturaCaja.objects.create(
            caja=Caja.objects.create(nombre_caja="Principal"),
            usuario=self.usuario,
            monto_inicial=Decimal("1000"),
        )
        self.venta = Venta.objects.create(importe_total=Decimal("500"))

    def movimiento(self, tipo, monto, **extra):
        return MovimientoCaja.objects.create(
            id_apertura=self.apertura,
            id_usuario=self.usuario,
            tipo_movimiento=tipo,
            concepto="prueba",
            monto=Decimal(monto),
            **extra,
        )

    def cobro(self, metodo, boleta):
        return Cobro.objects.create(
            venta=self.venta,
            monto=Decimal("500"),
            tipo_cobro="total",
            metodo_pago=metodo,
            numero_boleta=boleta,
        )

    def cerrar(self, contado):
        return CierreCaja.objects.create(
            id_apertura=self.apertura,
            id_usuario=self.usuario,
            efectivo_contado=Decimal(contado),
        )

    def test_cierre_calcula_totales_y_cierra_la_apertura(self):
        self.movimiento(TipoMovimiento.ENTRADA, "300")
        self.movimiento(TipoMovimiento.SALIDA, "100")

        cierre = self.cerrar("1150")

        self.assertEqual(cierre.total_ingresos, Decimal("300"))
        self.assertEqual(cierre.total_egresos, Decimal("100"))
        self.assertEqual(cierre.saldo_esperado, Decimal("1200"))
        self.assertEqual(cierre.diferencia, Decimal("-50"))
        self.apertura.refresh_from_db()
        self.assertEqual(self.apertura.estado, AperturaCaja.Estado.CERRADA)

    def test_no_se_cierra_dos_veces(self):
        self.cerrar("1000")
        with self.assertRaises(ValidationError):
            self.cerrar("1000")

    def test_no_hay_movimientos_en_apertura_cerrada(self):
        self.cerrar("1000")
        with self.assertRaises(ValidationError):
            self.movimiento(TipoMovimiento.ENTRADA, "10")

    def test_cobro_con_tarjeta_no_genera_movimiento(self):
        with self.assertRaises(ValidationError):
            self.movimiento(
                TipoMovimiento.ENTRADA, "500", id_cobro=self.cobro("Tarjeta", "B-1")
            )

    def test_cobro_en_efectivo_genera_entrada(self):
        cobro = self.cobro("Efectivo", "B-2")
        self.movimiento(TipoMovimiento.ENTRADA, "500", id_cobro=cobro)
        with self.assertRaises(ValidationError):
            self.movimiento(TipoMovimiento.SALIDA, "500", id_cobro=cobro)

    def test_monto_debe_ser_positivo(self):
        with self.assertRaises(ValidationError):
            self.movimiento(TipoMovimiento.ENTRADA, "0")

    def test_str_de_venta(self):
        self.assertEqual(str(self.venta), f"Venta #{self.venta.pk}")
