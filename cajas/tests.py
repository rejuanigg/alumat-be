from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import override_settings
from rest_framework.test import APITestCase

from .models import AperturaCaja, Caja


@override_settings(SECURE_SSL_REDIRECT=False)
class AperturaCajaTests(APITestCase):
    def setUp(self):
        self.usuario = get_user_model().objects.create_user(
            "cajera", "cajera@example.test", "clave-de-prueba-123"
        )
        self.otro = get_user_model().objects.create_user(
            "otra", "otra@example.test", "clave-de-prueba-123"
        )
        self.client.force_authenticate(self.usuario)
        self.caja = Caja.objects.create(nombre_caja="Principal")

    def abrir(self, caja=None, monto="100.00", **extra):
        return self.client.post(
            "/api/aperturas/",
            {"id_caja": (caja or self.caja).pk, "monto_inicial": monto, **extra},
            format="json",
        )

    def test_una_caja_no_tiene_dos_aperturas_abiertas(self):
        self.assertEqual(self.abrir().status_code, 201)
        r = self.abrir()
        self.assertEqual(r.status_code, 400)
        self.assertIn("id_caja", r.data)
        # El modelo también lo impide fuera de la API.
        with self.assertRaises(ValidationError):
            AperturaCaja.objects.create(caja=self.caja, usuario=self.usuario, monto_inicial=0)

    def test_no_se_abre_una_caja_inactiva(self):
        inactiva = Caja.objects.create(nombre_caja="Vieja", activa=False)
        r = self.abrir(caja=inactiva)
        self.assertEqual(r.status_code, 400)
        self.assertIn("id_caja", r.data)

    def test_monto_inicial_negativo_se_rechaza(self):
        r = self.abrir(monto="-1")
        self.assertEqual(r.status_code, 400)
        self.assertIn("monto_inicial", r.data)

    def test_el_usuario_es_el_autenticado(self):
        r = self.abrir(id_usuario=self.otro.pk)
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(r.data["id_usuario"], self.usuario.pk)
        self.assertEqual(AperturaCaja.objects.get().usuario, self.usuario)

    def test_tablas_del_der(self):
        self.assertEqual(Caja._meta.db_table, "cajas")
        self.assertEqual(AperturaCaja._meta.db_table, "apertura_cajas")
        self.assertEqual(Caja._meta.get_field("nombre_caja").max_length, 100)
