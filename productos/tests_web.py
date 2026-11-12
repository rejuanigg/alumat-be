"""Pantallas web de productos (reemplazan a las del antiguo catálogo)."""

from django.core.management import call_command
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from cuentas.models import Usuario

from .models import Diseno, Producto


@override_settings(
    SECURE_SSL_REDIRECT=False,
    STORAGES={
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
        }
    },
)
class ProductosWebTests(TestCase):
    def setUp(self):
        self.admin = Usuario.objects.create_superuser(
            "admin", "admin@example.test", "Temporal-segura-298!"
        )
        self.operador = Usuario.objects.create_user(
            "operador", "operador@example.test", "Temporal-segura-298!",
            estado="aprobado", is_active=True,
        )
        self.producto = Producto.objects.create(
            nombre="Ventana", tipo_abertura="Corrediza", stock=3
        )
        self.data = {
            "nombre": "Puerta",
            "tipo_abertura": "Batiente",
            "descripcion": "Texto",
            "stock": 5,
            "activo": "on",
        }

    def test_anonimo_no_lee_ni_escribe(self):
        for nombre, args in [
            ("lista", []),
            ("detalle", [self.producto.pk]),
            ("crear", []),
            ("editar", [self.producto.pk]),
            ("diseno_crear", [self.producto.pk]),
        ]:
            r = self.client.get(reverse("productos:" + nombre, args=args))
            self.assertEqual(r.status_code, 302)
        self.client.post(reverse("productos:crear"), self.data)
        self.assertEqual(Producto.objects.count(), 1)

    def test_alta_edicion_y_desactivacion(self):
        self.client.force_login(self.operador)
        self.client.post(reverse("productos:crear"), self.data)
        puerta = Producto.objects.get(nombre="Puerta")
        self.assertEqual(puerta.stock, 5)
        self.assertContains(self.client.get(puerta.get_absolute_url()), "Batiente")
        # Desactivar en lugar de borrar.
        datos = {**self.data, "stock": 7}
        del datos["activo"]
        self.client.post(reverse("productos:editar", args=[puerta.pk]), datos)
        puerta.refresh_from_db()
        self.assertEqual((puerta.stock, puerta.activo), (7, False))

    def test_repetido_y_stock_negativo(self):
        self.client.force_login(self.operador)
        r = self.client.post(
            reverse("productos:crear"),
            {**self.data, "nombre": " VENTANA ", "tipo_abertura": "corrediza"},
        )
        self.assertContains(r, "Ya existe un producto con ese nombre y tipo de abertura")
        r = self.client.post(reverse("productos:crear"), {**self.data, "stock": -1})
        self.assertIn("stock", r.context["form"].errors)
        self.assertEqual(Producto.objects.count(), 1)

    def test_disenos(self):
        self.client.force_login(self.operador)
        url = reverse("productos:diseno_crear", args=[self.producto.pk])
        self.client.post(url, {"nombre_diseno": "Dos hojas", "activo": "on"})
        diseno = Diseno.objects.get()
        self.assertEqual(diseno.producto, self.producto)
        r = self.client.post(url, {"nombre_diseno": "DOS HOJAS", "activo": "on"})
        self.assertContains(r, "El producto ya tiene un diseño con ese nombre")
        self.client.post(
            reverse("productos:diseno_editar", args=[diseno.pk]),
            {"nombre_diseno": "Dos hojas"},
        )
        diseno.refresh_from_db()
        self.assertFalse(diseno.activo)
        # A un producto inactivo no se le agregan diseños.
        Producto.objects.filter(pk=self.producto.pk).update(activo=False)
        r = self.client.post(url, {"nombre_diseno": "Tres hojas", "activo": "on"})
        self.assertContains(r, "producto inactivo")
        self.assertEqual(Diseno.objects.count(), 1)

    def test_busqueda_paginacion_y_escape_html(self):
        self.client.force_login(self.operador)
        self.producto.nombre = '<script>alert("x")</script>'
        self.producto.save()
        r = self.client.get(self.producto.get_absolute_url())
        self.assertNotContains(r, '<script>alert("x")</script>')
        self.assertContains(r, "&lt;script&gt;")
        lista = reverse("productos:lista")
        self.assertEqual(self.client.get(lista, {"q": "corred"}).context["paginator"].count, 1)
        self.assertContains(
            self.client.get(lista, {"q": "inexistente"}), "No encontramos coincidencias"
        )
        for n in range(13):
            Producto.objects.create(nombre=f"Producto {n}", tipo_abertura="Fija")
        self.assertEqual(len(self.client.get(lista).context["object_list"]), 12)
        self.assertEqual(len(self.client.get(lista, {"page": 2}).context["object_list"]), 2)

    def test_inicio_muestra_productos_con_menos_stock(self):
        Producto.objects.create(nombre="Ventiluz", tipo_abertura="Banderola", stock=0)
        self.client.force_login(self.operador)
        r = self.client.get(reverse("inicio:home"))
        self.assertEqual(r.context["productos"], 2)
        self.assertEqual([p.nombre for p in r.context["menos_stock"]], ["Ventiluz", "Ventana"])

    def test_csrf_impide_modificacion(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.operador)
        self.assertEqual(client.post(reverse("productos:crear"), self.data).status_code, 403)

    def test_demo_repetible_sin_sobrescribir(self):
        call_command("cargar_demo", usuario="admin", verbosity=0)
        ventana = Producto.objects.get(nombre="Ventana")
        ventana.stock = 999
        ventana.save()
        cantidades = (Producto.objects.count(), Diseno.objects.count())
        call_command("cargar_demo", usuario="admin", verbosity=0)
        ventana.refresh_from_db()
        self.assertEqual(ventana.stock, 999)
        self.assertEqual((Producto.objects.count(), Diseno.objects.count()), cantidades)

    def test_salud_y_pagina_inexistente(self):
        self.assertEqual(self.client.get(reverse("inicio:salud")).json(), {"estado": "ok"})
        self.client.force_login(self.operador)
        r = self.client.get(reverse("productos:detalle", args=[999999]))
        self.assertEqual(r.status_code, 404)
