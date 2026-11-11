from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from pedidos.models import Pedido

from .models import Cliente

URL = "/api/clientes/"

BASE = {
    "direccion": "Calle 123",
    "telefono": "3875555555",
    "correo_electronico": "cliente@example.com",
}
PARTICULAR = {**BASE, "tipo_cliente": "particular", "nombre": "Ana", "apellido": "Pérez", "dni": "30.123.456"}
EMPRESA = {**BASE, "tipo_cliente": "empresa", "razon_social": "Aluminios SA", "cuit": "20-12345678-6"}


class ClienteApiTests(APITestCase):
    def setUp(self):
        self.usuario = get_user_model().objects.create_user(
            username="operador",
            email="operador@example.test",
            password="clave-de-prueba-123",
        )
        self.client.force_authenticate(self.usuario)

    def crear(self, datos):
        return self.client.post(URL, datos, format="json")

    def test_sin_sesion_no_accede(self):
        self.client.force_authenticate(None)
        self.assertIn(
            self.client.get(URL).status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )

    def test_crea_particular_y_normaliza_dni(self):
        r = self.crear(PARTICULAR)
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.data)
        self.assertEqual(r.data["dni"], "30123456")

    def test_crea_empresa_y_normaliza_cuit(self):
        r = self.crear(EMPRESA)
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.data)
        self.assertEqual(r.data["cuit"], "20123456786")

    def test_empresa_sin_cuit_ni_razon_social(self):
        r = self.crear({**BASE, "tipo_cliente": "empresa"})
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("cuit", r.data)
        self.assertIn("razon_social", r.data)

    def test_particular_sin_datos(self):
        r = self.crear({**BASE, "tipo_cliente": "particular", "nombre": "   "})
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual({"nombre", "apellido", "dni"}, set(r.data))

    def test_campos_del_otro_tipo(self):
        r = self.crear({**PARTICULAR, "cuit": "20123456786"})
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("cuit", r.data)

    def test_formato_dni_y_cuit(self):
        self.assertIn("dni", self.crear({**PARTICULAR, "dni": "12ab"}).data)
        self.assertIn("cuit", self.crear({**EMPRESA, "cuit": "123"}).data)
        # Dígito verificador incorrecto.
        self.assertIn("cuit", self.crear({**EMPRESA, "cuit": "20123456781"}).data)

    def test_dni_y_cuit_repetidos(self):
        self.crear(PARTICULAR)
        self.crear(EMPRESA)
        r = self.crear({**PARTICULAR, "dni": "30123456"})
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        r = self.crear({**EMPRESA, "cuit": "20123456786"})
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

    def test_varias_empresas_sin_dni(self):
        self.assertEqual(self.crear(EMPRESA).status_code, status.HTTP_201_CREATED)
        otra = {**EMPRESA, "razon_social": "Otra SRL", "cuit": "30712345671"}
        self.assertEqual(self.crear(otra).status_code, status.HTTP_201_CREATED)

    def test_patch_valida_con_los_datos_actuales(self):
        id_cliente = self.crear(PARTICULAR).data["id_cliente"]
        # Cambiar a empresa sin cargar razón social ni CUIT no es válido.
        r = self.client.patch(f"{URL}{id_cliente}/", {"tipo_cliente": "empresa"}, format="json")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        r = self.client.patch(f"{URL}{id_cliente}/", {"telefono": "111"}, format="json")
        self.assertEqual(r.status_code, status.HTTP_200_OK, r.data)

    def test_no_se_borra_se_desactiva(self):
        id_cliente = self.crear(PARTICULAR).data["id_cliente"]
        Pedido.objects.create(cliente_id=id_cliente, usuario=self.usuario)
        r = self.client.delete(f"{URL}{id_cliente}/")
        self.assertEqual(r.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        r = self.client.patch(f"{URL}{id_cliente}/", {"activo": False}, format="json")
        self.assertEqual(r.status_code, status.HTTP_200_OK)

    def test_filtros_del_listado(self):
        self.crear(PARTICULAR)
        id_empresa = self.crear(EMPRESA).data["id_cliente"]
        Cliente.objects.filter(pk=id_empresa).update(activo=False)
        self.assertEqual(len(self.client.get(URL, {"activo": "true"}).data), 1)
        self.assertEqual(len(self.client.get(URL, {"tipo_cliente": "empresa"}).data), 1)

    def test_str(self):
        self.assertEqual(str(Cliente(tipo_cliente="particular", nombre="Ana", apellido="Pérez")), "Ana Pérez")
        self.assertEqual(str(Cliente(pk=5, tipo_cliente="empresa")), "Cliente #5")
