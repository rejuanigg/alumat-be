from django.core.exceptions import ValidationError
from django.db import IntegrityError, connection, transaction
from django.db.models import ProtectedError
from django.test import TestCase

from clientes.models import Cliente
from cuentas.models import Usuario
from productos.models import Diseno, Producto
from .models import DetallePedido, Pedido


class PedidoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.cliente = Cliente.objects.create(
            tipo_cliente=Cliente.TipoCliente.PARTICULAR,
            nombre="Ana",
            apellido="Pérez",
            dni="30111222",
            direccion="Belgrano 123",
            telefono="3874000000",
            correo_electronico="ana@example.test",
        )
        cls.usuario = Usuario.objects.create_user(
            "vendedor", "vendedor@example.test", "Temporal-segura-298!"
        )
        cls.producto = Producto.objects.create(
            nombre="Ventana corrediza", tipo_abertura="corrediza"
        )
        cls.diseno = Diseno.objects.create(
            producto=cls.producto, nombre_diseno="Dos hojas"
        )
        cls.otro_producto = Producto.objects.create(
            nombre="Puerta", tipo_abertura="batiente"
        )
        cls.otro_diseno = Diseno.objects.create(
            producto=cls.otro_producto, nombre_diseno="Una hoja"
        )

    def crear_pedido(self, **datos):
        datos = {"cliente": self.cliente, "usuario": self.usuario, **datos}
        return Pedido.objects.create(**datos)

    def datos_detalle(self, pedido, **datos):
        return {
            "pedido": pedido,
            "producto": self.producto,
            "diseno": self.diseno,
            "ancho": 1200,
            "alto": 1000,
            "cantidad": 2,
            "tipo_vidrio": "float 4 mm",
            "color_aluminio": "blanco",
            "tipo_revestimiento": "anodizado",
            **datos,
        }

    def con_restricciones_inmediatas(self):
        with connection.cursor() as cursor:
            cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")

    def test_registra_pedido_con_detalles(self):
        pedido = self.crear_pedido()
        DetallePedido.objects.create(**self.datos_detalle(pedido))
        DetallePedido.objects.create(**self.datos_detalle(pedido, cantidad=1))
        self.assertEqual(pedido.estado, Pedido.Estado.PENDIENTE)
        self.assertEqual(pedido.detalles.count(), 2)

    def test_no_registra_pedido_con_cliente_inexistente(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.con_restricciones_inmediatas()
            Pedido.objects.create(cliente_id=999999, usuario=self.usuario)

    def test_no_registra_pedido_con_usuario_inexistente(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.con_restricciones_inmediatas()
            Pedido.objects.create(cliente=self.cliente, usuario_id=999999)

    def test_no_registra_detalle_sin_pedido_existente(self):
        datos = self.datos_detalle(None)
        del datos["pedido"]
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.con_restricciones_inmediatas()
            DetallePedido.objects.create(pedido_id=999999, **datos)

    def test_no_registra_detalle_con_producto_o_diseno_inexistente(self):
        pedido = self.crear_pedido()
        for campo in ("producto", "diseno"):
            datos = self.datos_detalle(pedido)
            del datos[campo]
            with self.subTest(campo=campo):
                with self.assertRaises((IntegrityError, ValidationError)):
                    with transaction.atomic():
                        self.con_restricciones_inmediatas()
                        DetallePedido.objects.create(
                            **{f"{campo}_id": 999999}, **datos
                        )

    def test_rechaza_diseno_de_otro_producto(self):
        pedido = self.crear_pedido()
        detalle = DetallePedido(**self.datos_detalle(pedido, diseno=self.otro_diseno))
        with self.assertRaises(ValidationError) as error:
            detalle.full_clean()
        self.assertIn("diseno", error.exception.message_dict)
        with self.assertRaises(ValidationError):
            detalle.save()
        self.assertFalse(DetallePedido.objects.exists())

    def test_rechaza_estado_no_permitido(self):
        pedido = Pedido(cliente=self.cliente, usuario=self.usuario, estado="perdido")
        with self.assertRaises(ValidationError):
            pedido.full_clean()
        with self.assertRaises(IntegrityError), transaction.atomic():
            pedido.save()

    def test_rechaza_medidas_y_cantidad_no_positivas(self):
        pedido = self.crear_pedido()
        for campo in ("ancho", "alto", "cantidad"):
            with self.subTest(campo=campo):
                detalle = DetallePedido(**self.datos_detalle(pedido, **{campo: 0}))
                with self.assertRaises(ValidationError):
                    detalle.full_clean()
                with self.assertRaises(IntegrityError), transaction.atomic():
                    detalle.save()

    def test_restringe_borrado_de_padres_con_dependencias(self):
        pedido = self.crear_pedido()
        DetallePedido.objects.create(**self.datos_detalle(pedido))
        for padre in (pedido, self.cliente, self.usuario, self.diseno, self.producto):
            with self.subTest(padre=type(padre).__name__):
                with self.assertRaises(ProtectedError):
                    padre.delete()
