from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from rest_framework.test import APITestCase

from cajas.models import AperturaCaja, Caja
from ventas.models import Cobro, MetodoPago, Venta

from .models import CierreCaja, MovimientoCaja, TipoMovimiento

# Para las pruebas que renderizan páginas HTML (admin, 404) sin collectstatic.
PAGINAS_HTML = override_settings(
    SECURE_SSL_REDIRECT=False,
    STORAGES={
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
        }
    },
)


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
            apertura=self.apertura,
            usuario=self.usuario,
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
            apertura=self.apertura,
            usuario=self.usuario,
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
                TipoMovimiento.ENTRADA, "500", cobro=self.cobro(MetodoPago.TARJETA_DEBITO, "B-1")
            )

    def test_cobro_en_efectivo_genera_entrada(self):
        cobro = self.cobro(MetodoPago.EFECTIVO, "B-2")
        self.movimiento(TipoMovimiento.ENTRADA, "500", cobro=cobro)
        with self.assertRaises(ValidationError):
            self.movimiento(TipoMovimiento.SALIDA, "500", cobro=cobro)

    def test_un_cobro_genera_un_solo_movimiento(self):
        cobro = self.cobro(MetodoPago.EFECTIVO, "B-4")
        self.movimiento(TipoMovimiento.ENTRADA, "500", cobro=cobro)
        with self.assertRaises(ValidationError):
            self.movimiento(TipoMovimiento.ENTRADA, "500", cobro=cobro)

    def test_monto_debe_ser_positivo(self):
        with self.assertRaises(ValidationError):
            self.movimiento(TipoMovimiento.ENTRADA, "0")

    def test_str_de_venta(self):
        self.assertEqual(str(self.venta), f"Venta #{self.venta.pk}")


@PAGINAS_HTML
class CajaAdminTestCase(CajaTestCase):
    def test_admin_de_caja_es_de_solo_lectura(self):
        admin = get_user_model().objects.create_superuser(
            "jefa", "jefa@example.test", "clave-de-prueba-123"
        )
        self.client.force_login(admin)
        cierre = self.cerrar("1000")
        base = "/admin/movimientos_caja/cierrecaja/"
        self.assertEqual(self.client.get(base).status_code, 200)
        self.assertEqual(self.client.get(f"{base}add/").status_code, 403)
        self.assertEqual(self.client.get(f"{base}{cierre.pk}/delete/").status_code, 403)
        # Puede verlo, pero sin guardar cambios.
        r = self.client.post(f"{base}{cierre.pk}/change/", {"efectivo_contado": "1"})
        self.assertEqual(r.status_code, 403)


@PAGINAS_HTML
class CajaApiTestCase(CajaTestCase, APITestCase):
    def setUp(self):
        super().setUp()
        self.client.force_authenticate(self.usuario)

    def post(self, url, datos):
        return self.client.post(url, datos, format="json")

    def test_movimiento_por_api_usa_nombres_id(self):
        r = self.post(
            "/api/movimiento-caja/",
            {"id_apertura": self.apertura.pk, "tipo_movimiento": "ENTRADA",
             "concepto": "venta", "monto": "100.00"},
        )
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(r.json()["id_usuario"], self.usuario.pk)
        self.assertEqual(r.json()["id_apertura"], self.apertura.pk)

    def test_cobro_con_tarjeta_por_api_da_400(self):
        cobro = self.cobro(MetodoPago.TRANSFERENCIA, "B-3")
        r = self.post(
            "/api/movimiento-caja/",
            {"id_apertura": self.apertura.pk, "id_cobro": cobro.pk,
             "tipo_movimiento": "ENTRADA", "concepto": "cobro", "monto": "500.00"},
        )
        self.assertEqual(r.status_code, 400)
        self.assertIn("id_cobro", r.json())

    def test_cierre_por_api_y_segundo_cierre_da_409(self):
        datos = {"id_apertura": self.apertura.pk, "efectivo_contado": "1000.00"}
        r = self.post("/api/cierre-caja/", datos)
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(r.json()["saldo_esperado"], "1000.00")
        self.assertEqual(self.post("/api/cierre-caja/", datos).status_code, 409)
        r = self.post(
            "/api/movimiento-caja/",
            {"id_apertura": self.apertura.pk, "tipo_movimiento": "ENTRADA",
             "concepto": "tarde", "monto": "1.00"},
        )
        self.assertEqual(r.status_code, 409)

    def test_unico_procedimiento_de_cierre(self):
        # Ya no existe la vía que cerraba sin registrar el efectivo contado.
        r = self.post(f"/api/aperturas/{self.apertura.pk}/cerrar/", {})
        self.assertEqual(r.status_code, 404)
        self.apertura.refresh_from_db()
        self.assertEqual(self.apertura.estado, AperturaCaja.Estado.ABIERTA)

    def test_cobro_repetido_por_api_da_400(self):
        cobro = self.cobro(MetodoPago.EFECTIVO, "B-5")
        datos = {"id_apertura": self.apertura.pk, "id_cobro": cobro.pk,
                 "tipo_movimiento": "ENTRADA", "concepto": "cobro", "monto": "500.00"}
        self.assertEqual(self.post("/api/movimiento-caja/", datos).status_code, 201)
        r = self.post("/api/movimiento-caja/", datos)
        self.assertEqual(r.status_code, 400)
        self.assertIn("id_cobro", r.json())

    def test_cierre_se_corrige_pero_nada_se_borra(self):
        cierre = self.cerrar("1000")
        url = f"/api/cierre-caja/{cierre.pk}/"
        self.assertEqual(self.client.delete(url).status_code, 405)
        r = self.client.patch(url, {"efectivo_contado": "990"}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(r.json()["diferencia"], "-10.00")
        otra = AperturaCaja.objects.create(
            caja=Caja.objects.create(nombre_caja="Otra"),
            usuario=self.usuario,
            monto_inicial=Decimal("0"),
        )
        r = self.client.patch(url, {"id_apertura": otra.pk}, format="json")
        self.assertEqual(r.status_code, 400)
        movimiento = self.post(
            "/api/movimiento-caja/",
            {"id_apertura": otra.pk, "tipo_movimiento": "ENTRADA",
             "concepto": "x", "monto": "1.00"},
        ).json()
        url = f"/api/movimiento-caja/{movimiento['id_movimiento']}/"
        self.assertEqual(self.client.delete(url).status_code, 405)
        self.assertEqual(
            self.client.patch(url, {"monto": "5"}, format="json").status_code, 405
        )
