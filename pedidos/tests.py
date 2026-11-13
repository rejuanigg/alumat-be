from datetime import timedelta

from django.db import transaction
from django.test import TestCase, override_settings
from django.urls import Resolver404, resolve
from django.utils import timezone
from rest_framework.test import APIClient

from clientes.models import Cliente
from cuentas.models import Usuario
from productos.models import Diseno, Producto

from .models import DetallePedido, Pedido


@override_settings(SECURE_SSL_REDIRECT=False)
class PedidoTests(TestCase):
    def setUp(self):
        self.usuario = Usuario.objects.create_user(
            "operador", "operador@example.test", "Temporal-segura-298!",
            estado="aprobado", is_active=True,
        )
        self.api = APIClient()
        self.api.force_authenticate(self.usuario)
        self.ventana = Producto.objects.create(nombre="Ventana", tipo_abertura="Corrediza")
        self.diseno = Diseno.objects.create(producto=self.ventana, nombre_diseno="Base")
        cliente = Cliente.objects.create(
            tipo_cliente="particular", nombre="Ana", apellido="Pérez", dni="30123456",
            direccion="Calle 1", telefono="3875555555", correo_electronico="a@b.test",
        )
        self.pedido = Pedido.objects.create(cliente=cliente, usuario=self.usuario)
        DetallePedido.objects.create(
            pedido=self.pedido, diseno=self.diseno,
            ancho="1200.50", alto=1000, cantidad=3,
            tipo_vidrio="dvh_4_9_4", color_aluminio="blanco",
        )

    def avanzar(self, estado):
        return self.api.patch(
            f"/api/pedidos/{self.pedido.pk}/", {"estado": estado}, format="json"
        )

    def test_avanza_de_a_un_paso(self):
        r = self.avanzar("en_proceso")
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(self.avanzar("finalizado").status_code, 200)
        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.estado, "finalizado")

    def test_no_salta_estados(self):
        r = self.avanzar("finalizado")
        self.assertEqual(r.status_code, 400)
        self.assertIn("estado", r.data)

    def test_no_retrocede(self):
        self.avanzar("en_proceso")
        self.assertEqual(self.avanzar("pendiente").status_code, 400)

    def test_finalizado_no_admite_cambios(self):
        self.avanzar("en_proceso")
        self.avanzar("finalizado")
        r = self.api.patch(
            f"/api/pedidos/{self.pedido.pk}/", {"observaciones": "x"}, format="json"
        )
        self.assertEqual(r.status_code, 409)

    def test_no_pendiente_solo_avanza_estado(self):
        self.avanzar("en_proceso")
        r = self.api.patch(
            f"/api/pedidos/{self.pedido.pk}/", {"observaciones": "x"}, format="json"
        )
        self.assertEqual(r.status_code, 409)

    def test_no_hay_cancelacion(self):
        with self.assertRaises(Resolver404):
            resolve(f"/api/pedidos/{self.pedido.pk}/cancelar/")
        self.assertEqual(self.avanzar("cancelado").status_code, 400)

    def test_fecha_con_hora_y_no_futura(self):
        self.assertIsNotNone(self.pedido.fecha_pedido.hour)
        futura = (timezone.now() + timedelta(hours=1)).isoformat()
        r = self.api.patch(
            f"/api/pedidos/{self.pedido.pk}/", {"fecha_pedido": futura}, format="json"
        )
        self.assertEqual(r.status_code, 400)
        self.assertIn("fecha_pedido", r.data)

    def test_filtro_fecha_hasta_incluye_todo_el_dia(self):
        hoy = timezone.localdate().isoformat()
        r = self.api.get("/api/pedidos/", {"fecha_desde": hoy, "fecha_hasta": hoy})
        self.assertEqual(len(r.data), 1)

    def test_no_pendiente_no_admite_detalles_nuevos(self):
        self.avanzar("en_proceso")
        r = self.api.post(
            f"/api/pedidos/{self.pedido.pk}/detalles/",
            {
                "id_diseno": self.diseno.pk, "ancho": 800, "alto": 800,
                "color_aluminio": "blanco",
            },
            format="json",
        )
        self.assertEqual(r.status_code, 409)

    def test_pedido_desactualizado_da_409(self):
        # Otro usuario lo cambió después de que este lo cargó.
        Pedido.objects.filter(pk=self.pedido.pk).update(estado=Pedido.Estado.EN_PROCESO)
        from .views import PedidoViewSet

        with self.assertRaises(Exception) as error, transaction.atomic():
            PedidoViewSet().bloquear(self.pedido)
        self.assertEqual(error.exception.status_code, 409)


@override_settings(SECURE_SSL_REDIRECT=False)
class DetallePedidoTests(TestCase):
    def setUp(self):
        usuario = Usuario.objects.create_user(
            "operador", "operador@example.test", "Temporal-segura-298!",
            estado="aprobado", is_active=True,
        )
        self.api = APIClient()
        self.api.force_authenticate(usuario)
        self.producto = Producto.objects.create(nombre="Ventana", tipo_abertura="Corrediza")
        self.diseno = Diseno.objects.create(producto=self.producto, nombre_diseno="Base")
        cliente = Cliente.objects.create(
            tipo_cliente="particular", nombre="Ana", apellido="Pérez", dni="30123456",
        )
        self.pedido = Pedido.objects.create(cliente=cliente, usuario=usuario)
        self.url = f"/api/pedidos/{self.pedido.pk}/detalles/"
        self.datos = {
            "id_diseno": self.diseno.pk, "ancho": "1200.50", "alto": "1000",
            "cantidad": 2, "tipo_vidrio": "dvh_4_9_4", "color_aluminio": "negro",
        }

    def post(self, datos):
        return self.api.post(self.url, datos, format="json")

    def test_alta_con_medidas_decimales_y_listas(self):
        r = self.post(self.datos)
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(r.data["ancho"], "1200.50")
        self.assertNotIn("id_producto", r.data)
        self.assertEqual(r.data["tipo_revestimiento"], "")
        detalle = DetallePedido.objects.get()
        self.assertEqual(detalle.diseno.producto, self.producto)

    def test_cantidad_por_defecto_es_uno(self):
        datos = {**self.datos}
        del datos["cantidad"]
        r = self.post(datos)
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(r.data["cantidad"], 1)

    def test_color_obligatorio(self):
        datos = {**self.datos}
        del datos["color_aluminio"]
        self.assertIn("color_aluminio", self.post(datos).data)

    def test_valores_fuera_de_las_listas(self):
        r = self.post({**self.datos, "tipo_vidrio": "Float", "color_aluminio": "Rojo"})
        self.assertEqual(r.status_code, 400)
        self.assertEqual({"tipo_vidrio", "color_aluminio"}, set(r.data))
        r = self.post({**self.datos, "tipo_revestimiento": "madera"})
        self.assertIn("tipo_revestimiento", r.data)

    def test_medidas_y_cantidad_positivas(self):
        r = self.post({**self.datos, "ancho": "0", "alto": "-1", "cantidad": 0})
        self.assertEqual({"ancho", "alto", "cantidad"}, set(r.data))

    def test_detalle_repetido(self):
        self.assertEqual(self.post(self.datos).status_code, 201)
        r = self.post({**self.datos, "cantidad": 5})
        self.assertEqual(r.status_code, 400)
        r = self.post({**self.datos, "color_aluminio": "blanco"})
        self.assertEqual(r.status_code, 201)

    def test_producto_inactivo_del_diseno(self):
        self.producto.activo = False
        self.producto.save()
        r = self.post(self.datos)
        self.assertEqual(r.status_code, 400)
        self.assertIn("id_diseno", r.data)
