from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from cuentas.models import Usuario
from .models import Categoria, Producto


@override_settings(
    SECURE_SSL_REDIRECT=False,
    STORAGES={
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
        }
    },
)
class CatalogoTests(TestCase):
    def setUp(self):
        self.admin = Usuario.objects.create_superuser(
            "admin", "admin@example.test", "Temporal-segura-298!"
        )
        self.operador = Usuario.objects.create_user(
            "operador",
            "operador@example.test",
            "Temporal-segura-298!",
            estado="aprobado",
            is_active=True,
        )
        self.categoria = Categoria.objects.create(nombre="Librería")
        self.producto = Producto.objects.create(
            codigo="P-01",
            nombre="Cuaderno",
            categoria=self.categoria,
            precio="100.00",
            stock=2,
            creado_por=self.admin,
            actualizado_por=self.admin,
        )
        self.data = {
            "codigo": "p-02",
            "nombre": "Otro",
            "categoria": self.categoria.pk,
            "descripcion": "Texto",
            "precio": "20.50",
            "stock": 5,
        }

    def test_anonimo_no_lee_ni_escribe(self):
        for name, args in [
            ("lista", []),
            ("detalle", [self.producto.pk]),
            ("crear", []),
            ("editar", [self.producto.pk]),
            ("eliminar", [self.producto.pk]),
            ("categorias", []),
        ]:
            self.assertEqual(
                self.client.get(reverse("catalogo:" + name, args=args)).status_code, 302
            )
        self.assertEqual(
            self.client.post(reverse("catalogo:crear"), self.data).status_code, 302
        )
        self.assertEqual(Producto.objects.count(), 1)

    def test_ciclo_completo_y_autoria(self):
        self.client.force_login(self.operador)
        self.data["creado_por"] = self.admin.pk
        self.client.post(reverse("catalogo:crear"), self.data)
        producto = Producto.objects.get(codigo="P-02")
        self.assertEqual(producto.creado_por, self.operador)
        self.assertContains(self.client.get(producto.get_absolute_url()), "Otro")
        self.data["nombre"] = "Actualizado"
        self.client.post(reverse("catalogo:editar", args=[producto.pk]), self.data)
        producto.refresh_from_db()
        self.assertEqual(producto.nombre, "Actualizado")
        self.assertEqual(
            self.client.post(
                reverse("catalogo:eliminar", args=[producto.pk])
            ).status_code,
            403,
        )
        self.assertTrue(Producto.objects.filter(pk=producto.pk).exists())
        self.client.force_login(self.admin)
        self.assertEqual(
            self.client.get(
                reverse("catalogo:eliminar", args=[producto.pk])
            ).status_code,
            200,
        )
        self.assertTrue(Producto.objects.filter(pk=producto.pk).exists())
        self.client.post(reverse("catalogo:eliminar", args=[producto.pk]))
        self.assertFalse(Producto.objects.filter(pk=producto.pk).exists())

    def test_precio_stock_y_categoria_invalidos(self):
        self.client.force_login(self.operador)
        for field, value in [("precio", "-1"), ("stock", "-1"), ("categoria", 999999)]:
            data = {**self.data, field: value}
            response = self.client.post(reverse("catalogo:crear"), data)
            self.assertEqual(response.status_code, 200)
            self.assertIn(field, response.context["form"].errors)
        self.assertEqual(Producto.objects.count(), 1)

    def test_codigo_duplicado_y_espacios(self):
        self.client.force_login(self.operador)
        self.data["codigo"] = " p-01 "
        response = self.client.post(reverse("catalogo:crear"), self.data)
        self.assertIn("codigo", response.context["form"].errors)

    def test_restriccion_precio_en_base(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Producto.objects.filter(pk=self.producto.pk).update(precio=-1)

    def test_categoria_con_productos_no_se_borra(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("catalogo:categoria_eliminar", args=[self.categoria.pk])
        )
        self.assertContains(
            response, "No se puede eliminar una categoría con productos"
        )
        self.assertTrue(Categoria.objects.filter(pk=self.categoria.pk).exists())

    def test_crud_categorias_y_permisos(self):
        self.client.force_login(self.operador)
        self.assertEqual(
            self.client.post(
                reverse("catalogo:categoria_crear"), {"nombre": "Nueva"}
            ).status_code,
            403,
        )
        self.client.force_login(self.admin)
        self.client.post(reverse("catalogo:categoria_crear"), {"nombre": "Nueva"})
        c = Categoria.objects.get(nombre="Nueva")
        self.client.post(
            reverse("catalogo:categoria_editar", args=[c.pk]), {"nombre": "Actualizada"}
        )
        c.refresh_from_db()
        self.assertEqual(c.nombre, "Actualizada")
        self.client.post(reverse("catalogo:categoria_eliminar", args=[c.pk]))
        self.assertFalse(Categoria.objects.filter(pk=c.pk).exists())

    def test_busqueda_paginacion_y_escape_html(self):
        self.client.force_login(self.operador)
        self.producto.nombre = '<script>alert("x")</script>'
        self.producto.save()
        response = self.client.get(self.producto.get_absolute_url())
        self.assertNotContains(response, '<script>alert("x")</script>')
        self.assertContains(response, "&lt;script&gt;")
        self.assertEqual(
            self.client.get(reverse("catalogo:lista"), {"q": "P-01"})
            .context["paginator"]
            .count,
            1,
        )
        self.assertContains(
            self.client.get(reverse("catalogo:lista"), {"q": "inexistente"}),
            "No encontramos coincidencias",
        )
        for n in range(13):
            Producto.objects.create(
                codigo=f"OTRO-{n}",
                nombre=f"Producto {n}",
                categoria=self.categoria,
                precio=1,
                stock=0,
                creado_por=self.admin,
                actualizado_por=self.admin,
            )
        self.assertEqual(
            len(self.client.get(reverse("catalogo:lista")).context["object_list"]), 12
        )
        self.assertEqual(
            len(
                self.client.get(reverse("catalogo:lista"), {"page": 2}).context[
                    "object_list"
                ]
            ),
            2,
        )

    def test_csrf_impide_modificacion(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.operador)
        self.assertEqual(
            client.post(reverse("catalogo:crear"), self.data).status_code, 403
        )

    def test_demo_repetible_sin_sobrescribir(self):
        call_command("cargar_demo", usuario="admin", verbosity=0)
        p = Producto.objects.get(codigo="DEMO-001")
        p.stock = 999
        p.save()
        cantidad = Producto.objects.count()
        call_command("cargar_demo", usuario="admin", verbosity=0)
        p.refresh_from_db()
        self.assertEqual(p.stock, 999)
        self.assertEqual(Producto.objects.count(), cantidad)

    def test_salud_y_pagina_inexistente(self):
        self.assertEqual(
            self.client.get(reverse("inicio:salud")).json(), {"estado": "ok"}
        )
        self.client.force_login(self.operador)
        self.assertEqual(
            self.client.get(reverse("catalogo:detalle", args=[999999])).status_code, 404
        )
