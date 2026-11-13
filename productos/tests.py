from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from cajas.models import AperturaCaja, Caja
from clientes.models import Cliente
from cuentas.models import Usuario
from movimientos_caja.models import CierreCaja
from pedidos.models import Pedido
from ventas.models import Cobro, Venta
from .models import Diseno, Producto


@override_settings(SECURE_SSL_REDIRECT=False)
class ValidacionesApiTests(TestCase):
    def setUp(self):
        self.usuario = Usuario.objects.create_user(
            "operador",
            "operador@example.test",
            "Temporal-segura-298!",
            estado="aprobado",
            is_active=True,
        )
        self.api = APIClient()
        self.api.force_authenticate(self.usuario)
        self.producto = Producto.objects.create(
            nombre="Ventana", tipo_abertura="Corrediza"
        )
        self.diseno = Diseno.objects.create(
            producto=self.producto, nombre_diseno="Dos hojas"
        )

    def post(self, url, datos):
        return self.api.post(url, datos, format="json")

    # Productos y diseños

    def test_producto_repetido_sin_importar_mayusculas(self):
        r = self.post(
            "/api/productos/", {"nombre": " VENTANA ", "tipo_abertura": "corrediza"}
        )
        self.assertEqual(r.status_code, 400)
        self.assertIn("nombre", r.data)
        self.assertEqual(Producto.objects.count(), 1)

    def test_mismo_nombre_con_otro_tipo_de_abertura_se_permite(self):
        r = self.post("/api/productos/", {"nombre": "Ventana", "tipo_abertura": "Batiente"})
        self.assertEqual(r.status_code, 201)

    def test_editar_producto_hacia_un_repetido(self):
        otro = Producto.objects.create(nombre="Puerta", tipo_abertura="Corrediza")
        r = self.api.patch(
            f"/api/productos/{otro.pk}/", {"nombre": "ventana"}, format="json"
        )
        self.assertEqual(r.status_code, 400)
        r = self.api.patch(
            f"/api/productos/{self.producto.pk}/", {"descripcion": "x"}, format="json"
        )
        self.assertEqual(r.status_code, 200)

    def test_nombre_vacio(self):
        r = self.post("/api/productos/", {"nombre": "   ", "tipo_abertura": "Fija"})
        self.assertEqual(r.status_code, 400)

    def test_diseno_repetido_en_el_mismo_producto(self):
        r = self.post(
            "/api/disenos/",
            {"id_producto": self.producto.pk, "nombre_diseno": "dos HOJAS"},
        )
        self.assertEqual(r.status_code, 400)
        self.assertIn("nombre_diseno", r.data)

    def test_diseno_en_producto_inactivo(self):
        inactivo = Producto.objects.create(
            nombre="Vieja", tipo_abertura="Fija", activo=False
        )
        r = self.post(
            "/api/disenos/", {"id_producto": inactivo.pk, "nombre_diseno": "A"}
        )
        self.assertEqual(r.status_code, 400)

    # Clientes

    def particular(self, **cambios):
        datos = {
            "tipo_cliente": "particular",
            "nombre": "Ana",
            "apellido": "Pérez",
            "dni": "30.123.456",
            "direccion": "Calle 1",
            "telefono": "+54 381 555-1234",
            "correo_electronico": "Ana@Example.test",
        }
        datos.update(cambios)
        return datos

    def test_cliente_dni_repetido(self):
        self.assertEqual(self.post("/api/clientes/", self.particular()).status_code, 201)
        cliente = Cliente.objects.get()
        self.assertEqual(cliente.dni, "30123456")
        self.assertEqual(cliente.correo_electronico, "ana@example.test")
        r = self.post("/api/clientes/", self.particular(dni="30123456"))
        self.assertEqual(r.status_code, 400)
        self.assertIn("dni", r.data)

    def test_cliente_campos_obligatorios_segun_tipo(self):
        r = self.post("/api/clientes/", self.particular(dni="", apellido=""))
        self.assertEqual(r.status_code, 400)
        self.assertEqual(set(r.data), {"dni", "apellido"})
        r = self.post("/api/clientes/", self.particular(tipo_cliente="empresa"))
        # Además, una empresa no lleva nombre, apellido ni DNI.
        self.assertEqual(
            set(r.data), {"razon_social", "cuit", "nombre", "apellido", "dni"}
        )

    def test_cliente_formatos(self):
        r = self.post("/api/clientes/", self.particular(dni="12ab", telefono="hola"))
        self.assertEqual(set(r.data), {"dni", "telefono"})

    def test_empresa_cuit(self):
        empresa = self.particular(
            tipo_cliente="empresa", razon_social="Vidrios SA", nombre="", apellido="",
            dni="", cuit="20-12345678-0",
        )
        self.assertEqual(self.post("/api/clientes/", empresa).status_code, 400)
        empresa["cuit"] = "20123456786"
        self.assertEqual(self.post("/api/clientes/", empresa).status_code, 201)
        # El CUIT se guarda con el formato del diccionario.
        self.assertEqual(Cliente.objects.get().cuit, "20-12345678-6")
        empresa["cuit"] = "20-12345678-6"
        r = self.post("/api/clientes/", empresa)
        self.assertEqual(r.status_code, 400)
        self.assertIn("cuit", r.data)

    # Pedidos

    def crear_cliente(self, **datos):
        return Cliente.objects.create(
            tipo_cliente="particular", nombre="A", apellido="B", dni="1234567",
            direccion="x", telefono="123456", correo_electronico="a@b.test", **datos
        )

    def test_pedido_cliente_inactivo_y_fecha_futura(self):
        cliente = self.crear_cliente(activo=False)
        r = self.post(
            "/api/pedidos/", {"id_cliente": cliente.pk, "fecha_pedido": "2999-01-01"}
        )
        self.assertEqual(set(r.data), {"id_cliente", "fecha_pedido"})

    def test_detalle_repetido_en_el_mismo_pedido(self):
        pedido = Pedido.objects.create(cliente=self.crear_cliente(), usuario=self.usuario)
        detalle = {
            "id_diseno": self.diseno.pk,
            "ancho": 1200,
            "alto": 1000,
            "cantidad": 1,
            "tipo_vidrio": "simple_4",
            "color_aluminio": "blanco",
        }
        url = f"/api/pedidos/{pedido.pk}/detalles/"
        self.assertEqual(self.post(url, detalle).status_code, 201)
        r = self.post(url, {**detalle, "cantidad": 3})
        self.assertEqual(r.status_code, 400)
        r = self.post(url, {**detalle, "ancho": 1500})
        self.assertEqual(r.status_code, 201)

    def test_detalle_con_diseno_inactivo(self):
        pedido = Pedido.objects.create(cliente=self.crear_cliente(), usuario=self.usuario)
        self.diseno.activo = False
        self.diseno.save()
        r = self.post(
            f"/api/pedidos/{pedido.pk}/detalles/",
            {
                "id_diseno": self.diseno.pk,
                "ancho": 1, "alto": 1, "cantidad": 1, "color_aluminio": "blanco",
            },
        )
        self.assertEqual(r.status_code, 400)
        self.assertIn("id_diseno", r.data)

    # Cajas, movimientos y cierres

    def test_caja_repetida(self):
        Caja.objects.create(nombre_caja="Caja principal")
        r = self.post("/api/cajas/", {"nombre_caja": "caja PRINCIPAL"})
        self.assertEqual(r.status_code, 400)
        self.assertIn("nombre_caja", r.data)

    def test_movimientos_y_cierre(self):
        apertura = AperturaCaja.objects.create(
            caja=Caja.objects.create(nombre_caja="C1"),
            usuario=self.usuario,
            monto_inicial=100,
        )
        movimiento = {
            "id_apertura": apertura.pk,
            "tipo_movimiento": "entrada",
            "concepto": "Venta",
            "monto": "0",
        }
        r = self.post("/api/movimiento-caja/", movimiento)
        self.assertIn("monto", r.data)

        pedido = Pedido.objects.create(cliente=self.crear_cliente(), usuario=self.usuario)
        venta = Venta.objects.create(pedido=pedido, usuario=self.usuario, importe_total=50)
        tarjeta = Cobro.objects.create(
            venta=venta, usuario=self.usuario, monto=50, tipo_cobro="total",
            metodo_pago=Cobro.MetodoPago.TARJETA_DEBITO,
            numero_boleta="B-1",
        )
        r = self.post("/api/movimiento-caja/", {**movimiento, "monto": "50", "id_cobro": tarjeta.pk})
        self.assertIn("id_cobro", r.data)

        efectivo = Cobro.objects.create(
            venta=venta, usuario=self.usuario, monto=50, tipo_cobro="total",
            metodo_pago=Cobro.MetodoPago.EFECTIVO,
            numero_boleta="B-2",
        )
        con_cobro = {**movimiento, "monto": "50", "id_cobro": efectivo.pk}
        self.assertEqual(self.post("/api/movimiento-caja/", con_cobro).status_code, 201)
        r = self.post("/api/movimiento-caja/", con_cobro)
        self.assertIn("id_cobro", r.data)

        cierre = {"id_apertura": apertura.pk, "efectivo_contado": "-1"}
        self.assertIn("efectivo_contado", self.post("/api/cierre-caja/", cierre).data)
        cierre["efectivo_contado"] = "140"
        r = self.post("/api/cierre-caja/", cierre)
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data["diferencia"], "-10.00")
        # Cerrar otra vez una apertura cerrada: 409 (el estado no lo permite).
        self.assertEqual(self.post("/api/cierre-caja/", cierre).status_code, 409)

        # El cierre es definitivo: no se corrige.
        r = self.api.patch(
            f"/api/cierre-caja/{r.data['id_cierre']}/", {"efectivo_contado": "150"},
            format="json",
        )
        self.assertEqual(r.status_code, 405)
        self.assertEqual(CierreCaja.objects.get().diferencia, -10)

        r = self.post("/api/movimiento-caja/", {**movimiento, "monto": "5"})
        self.assertEqual(r.status_code, 409)
