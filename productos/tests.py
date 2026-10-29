from django.db import IntegrityError, connection, transaction
from django.db.models import ProtectedError
from django.test import TestCase
from .models import Diseno, Producto


class RelacionProductoDisenoTests(TestCase):
    def setUp(self):
        self.producto = Producto.objects.create(
            nombre="Ventana corrediza", tipo_abertura="corrediza"
        )

    def test_producto_tiene_varios_disenos(self):
        Diseno.objects.create(producto=self.producto, nombre_diseno="Dos hojas")
        Diseno.objects.create(producto=self.producto, nombre_diseno="Tres hojas")
        self.assertEqual(self.producto.disenos.count(), 2)

    def test_no_registra_diseno_con_producto_inexistente(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")
            Diseno.objects.create(producto_id=999999, nombre_diseno="Huérfano")

    def test_no_borra_producto_con_disenos(self):
        Diseno.objects.create(producto=self.producto, nombre_diseno="Dos hojas")
        with self.assertRaises(ProtectedError):
            self.producto.delete()
        self.assertTrue(Producto.objects.filter(pk=self.producto.pk).exists())

    def test_borra_producto_sin_disenos(self):
        self.producto.delete()
        self.assertFalse(Producto.objects.exists())

    def test_desactivar_conserva_registros(self):
        diseno = Diseno.objects.create(
            producto=self.producto, nombre_diseno="Dos hojas"
        )
        Producto.objects.filter(pk=self.producto.pk).update(activo=False)
        Diseno.objects.filter(pk=diseno.pk).update(activo=False)
        diseno.refresh_from_db()
        self.assertFalse(diseno.activo)
        self.assertFalse(diseno.producto.activo)
        self.assertEqual(diseno.producto, self.producto)
