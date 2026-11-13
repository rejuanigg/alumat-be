from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from cuentas.models import Usuario
from cuentas.permisos import GRUPO_DUENO, GRUPO_VENDEDOR, es_dueno
from productos.models import Producto

# Para las pantallas HTML (403) sin collectstatic.
SIN_MANIFIESTO = override_settings(
    SECURE_SSL_REDIRECT=False,
    STORAGES={
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"}
    },
)

CLIENTE = {"tipo_cliente": "particular", "nombre": "Ana", "apellido": "Pérez", "dni": "30123456"}


@SIN_MANIFIESTO
class RolesTests(TestCase):
    def setUp(self):
        call_command("crear_roles", verbosity=0)
        self.vendedor = self.usuario("vendedor", GRUPO_VENDEDOR)
        self.dueno = self.usuario("dueno", GRUPO_DUENO)
        self.api = APIClient()

    def usuario(self, nombre, grupo):
        usuario = Usuario.objects.create_user(
            nombre, f"{nombre}@example.test", "Temporal-segura-298!",
            estado="aprobado", is_active=True,
        )
        usuario.groups.add(Group.objects.get(name=grupo))
        return usuario

    def test_crear_roles_es_repetible(self):
        call_command("crear_roles", verbosity=0)
        call_command("crear_roles", verbosity=0)
        self.assertEqual(
            sorted(Group.objects.values_list("name", flat=True)), sorted([GRUPO_DUENO, GRUPO_VENDEDOR])
        )

    def test_dueno_consulta_pero_no_modifica_clientes(self):
        self.api.force_authenticate(self.vendedor)
        id_cliente = self.api.post("/api/clientes/", CLIENTE, format="json").data["id_cliente"]
        self.api.force_authenticate(self.dueno)
        self.assertEqual(self.api.get("/api/clientes/").status_code, 200)
        self.assertEqual(self.api.get(f"/api/clientes/{id_cliente}/").status_code, 200)
        r = self.api.post("/api/clientes/", {**CLIENTE, "dni": "30123457"}, format="json")
        self.assertEqual(r.status_code, 403)
        self.assertEqual(r.data["detail"], "El Dueño solo puede consultar información.")
        r = self.api.patch(f"/api/clientes/{id_cliente}/", {"activo": False}, format="json")
        self.assertEqual(r.status_code, 403)

    def test_dueno_consulta_pero_no_modifica_cajas(self):
        self.api.force_authenticate(self.vendedor)
        id_caja = self.api.post("/api/cajas/", {"nombre_caja": "Principal"}, format="json").data["id_caja"]
        self.api.force_authenticate(self.dueno)
        self.assertEqual(self.api.get("/api/cajas/").status_code, 200)
        self.assertEqual(
            self.api.post("/api/cajas/", {"nombre_caja": "Otra"}, format="json").status_code, 403
        )
        self.assertEqual(
            self.api.patch(f"/api/cajas/{id_caja}/", {"activa": False}, format="json").status_code, 403
        )
        self.assertEqual(
            self.api.post("/api/aperturas/", {"id_caja": id_caja, "monto_inicial": "0"}, format="json").status_code,
            403,
        )

    def test_vendedor_puede_dar_altas(self):
        self.api.force_authenticate(self.vendedor)
        self.assertEqual(self.api.post("/api/clientes/", CLIENTE, format="json").status_code, 201)
        self.assertEqual(
            self.api.post("/api/cajas/", {"nombre_caja": "Principal"}, format="json").status_code, 201
        )

    def test_sin_sesion_recibe_403(self):
        self.assertEqual(self.api.get("/api/clientes/").status_code, 403)
        self.assertEqual(self.api.post("/api/cajas/", {"nombre_caja": "X"}, format="json").status_code, 403)

    def test_superusuario_en_grupo_dueno_sigue_operando(self):
        admin = Usuario.objects.create_superuser("admin", "admin@example.test", "Temporal-segura-298!")
        admin.groups.add(Group.objects.get(name=GRUPO_DUENO))
        self.assertFalse(es_dueno(admin))
        self.api.force_authenticate(admin)
        self.assertEqual(self.api.post("/api/clientes/", CLIENTE, format="json").status_code, 201)

    def test_dueno_no_entra_a_crear_ni_editar_productos(self):
        producto = Producto.objects.create(nombre="Ventana", tipo_abertura="Corrediza")
        self.client.force_login(self.dueno)
        self.assertEqual(self.client.get(reverse("productos:lista")).status_code, 200)
        self.assertEqual(self.client.get(producto.get_absolute_url()).status_code, 200)
        for url in (reverse("productos:crear"), reverse("productos:editar", args=[producto.pk])):
            self.assertEqual(self.client.get(url).status_code, 403)
            self.assertEqual(
                self.client.post(url, {"nombre": "Puerta", "tipo_abertura": "Batiente"}).status_code, 403
            )
        self.assertEqual(Producto.objects.count(), 1)
        self.client.force_login(self.vendedor)
        self.assertEqual(self.client.get(reverse("productos:crear")).status_code, 200)
