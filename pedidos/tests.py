from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from clientes.models import Cliente
from cuentas.models import Usuario
from productos.models import Diseno, Producto

from .models import DetallePedido, Pedido
from .stock import sincronizar_stock


@override_settings(SECURE_SSL_REDIRECT=False)
class StockTests(TestCase):
    def setUp(self):
        self.usuario = Usuario.objects.create_user(
            "operador", "operador@example.test", "Temporal-segura-298!",
            estado="aprobado", is_active=True,
        )
        self.api = APIClient()
        self.api.force_authenticate(self.usuario)
        self.ventana = Producto.objects.create(
            nombre="Ventana", tipo_abertura="Corrediza", stock=10
        )
        self.puerta = Producto.objects.create(
            nombre="Puerta", tipo_abertura="Batiente", stock=2
        )
        cliente = Cliente.objects.create(
            tipo_cliente="particular", nombre="Ana", apellido="Pérez", dni="30123456",
            direccion="Calle 1", telefono="3875555555", correo_electronico="a@b.test",
        )
        self.pedido = Pedido.objects.create(cliente=cliente, usuario=self.usuario)
        self.detalle(self.ventana, 3, ancho=1200)
        self.detalle(self.ventana, 2, ancho=800)  # mismo producto, otras medidas
        self.detalle(self.puerta, 1)

    def detalle(self, producto, cantidad, ancho=1000):
        DetallePedido.objects.create(
            pedido=self.pedido,
            producto=producto,
            diseno=Diseno.objects.get_or_create(producto=producto, nombre_diseno="Base")[0],
            ancho=ancho, alto=1000, cantidad=cantidad,
            tipo_vidrio="Float", color_aluminio="Blanco", tipo_revestimiento="Ninguno",
        )

    def avanzar(self, estado):
        return self.api.patch(
            f"/api/pedidos/{self.pedido.pk}/", {"estado": estado}, format="json"
        )

    def cancelar(self):
        return self.api.post(f"/api/pedidos/{self.pedido.pk}/cancelar/")

    def stock(self):
        self.ventana.refresh_from_db()
        self.puerta.refresh_from_db()
        return self.ventana.stock, self.puerta.stock

    def test_pendiente_no_descuenta(self):
        self.assertEqual(self.stock(), (10, 2))

    def test_descuenta_al_pasar_a_produccion_sin_importar_medidas(self):
        r = self.avanzar("en_produccion")
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(self.stock(), (5, 1))

    def test_no_descuenta_dos_veces(self):
        self.avanzar("en_produccion")
        self.avanzar("terminado")
        self.avanzar("entregado")
        self.assertEqual(self.stock(), (5, 1))
        # Llamarlo de nuevo con el pedido ya descontado no cambia nada.
        self.pedido.refresh_from_db()
        sincronizar_stock(self.pedido)
        self.assertEqual(self.stock(), (5, 1))

    def test_saltar_de_pendiente_a_entregado_tambien_descuenta(self):
        self.assertEqual(self.avanzar("entregado").status_code, 200)
        self.assertEqual(self.stock(), (5, 1))

    def test_cancelar_devuelve_lo_descontado(self):
        self.avanzar("en_produccion")
        self.assertEqual(self.cancelar().status_code, 200)
        self.assertEqual(self.stock(), (10, 2))
        self.pedido.refresh_from_db()
        self.assertFalse(self.pedido.stock_descontado)

    def test_cancelar_pendiente_no_toca_el_stock(self):
        self.assertEqual(self.cancelar().status_code, 200)
        self.assertEqual(self.stock(), (10, 2))

    def test_sin_stock_suficiente_rechaza_y_no_cambia_nada(self):
        self.puerta.stock = 0
        self.puerta.save()
        r = self.avanzar("en_produccion")
        self.assertEqual(r.status_code, 409)
        self.assertIn("Puerta: hay 0, se necesitan 1", r.data["detail"])
        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.estado, Pedido.Estado.PENDIENTE)
        self.assertFalse(self.pedido.stock_descontado)
        self.assertEqual(self.stock(), (10, 0))

    def test_pedido_desactualizado_da_409(self):
        # Otro usuario lo canceló después de que este lo cargó.
        Pedido.objects.filter(pk=self.pedido.pk).update(estado=Pedido.Estado.CANCELADO)
        from .views import PedidoViewSet

        with self.assertRaises(Exception) as error, transaction.atomic():
            PedidoViewSet().bloquear(self.pedido)
        self.assertEqual(error.exception.status_code, 409)

    def test_stock_negativo_bloqueado_en_la_base(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Producto.objects.filter(pk=self.puerta.pk).update(stock=-1)

    def test_stock_visible_en_la_api_de_productos(self):
        r = self.api.get(f"/api/productos/{self.ventana.pk}/")
        self.assertEqual(r.data["stock"], 10)
        r = self.api.patch(
            f"/api/productos/{self.ventana.pk}/", {"stock": 25}, format="json"
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self.stock()[0], 25)
