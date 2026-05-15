from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from clientes.models import Cliente
from config.choices import EstadoEnvio, EstadoGeneral, TipoDocumento
from envios.models import Empleado, Encomienda, HistorialEstado
from rutas.models import Ruta


class ApiBaseTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            username="apiuser",
            email="apiuser@example.com",
            password="admin123",
        )
        cls.empleado = Empleado.objects.create(
            codigo="EMPAPI",
            nombres="Api",
            apellidos="User",
            cargo="Operador",
            email="apiuser@example.com",
            estado=EstadoGeneral.ACTIVO,
            fecha_ingreso=timezone.now().date(),
        )
        cls.remitente = Cliente.objects.create(
            tipo_doc=TipoDocumento.DNI,
            nro_doc="12345678",
            nombres="Carlos",
            apellidos="Ramirez",
            estado=EstadoGeneral.ACTIVO,
        )
        cls.destinatario = Cliente.objects.create(
            tipo_doc=TipoDocumento.DNI,
            nro_doc="87654321",
            nombres="Ana",
            apellidos="Torres",
            estado=EstadoGeneral.ACTIVO,
        )
        cls.ruta = Ruta.objects.create(
            codigo="LIM-TRU",
            origen="Lima",
            destino="Trujillo",
            precio_base=Decimal("25.00"),
            dias_entrega=2,
            estado=EstadoGeneral.ACTIVO,
        )
        cls.encomienda = Encomienda.objects.create(
            codigo="ENC-API-001",
            descripcion="Caja de prueba",
            peso_kg=Decimal("2.50"),
            remitente=cls.remitente,
            destinatario=cls.destinatario,
            ruta=cls.ruta,
            empleado_registro=cls.empleado,
            costo_envio=Decimal("25.00"),
            fecha_entrega_est=timezone.now().date() + timedelta(days=2),
        )

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(self.user)


class ApiAuthTests(ApiBaseTestCase):
    def test_obtener_token_jwt(self):
        client = APIClient()
        response = client.post(
            "/api/v1/auth/token/",
            {"username": "apiuser", "password": "admin123"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_verificar_token_jwt(self):
        client = APIClient()
        token_response = client.post(
            "/api/v1/auth/token/",
            {"username": "apiuser", "password": "admin123"},
            format="json",
        )
        response = client.post(
            "/api/v1/auth/token/verify/",
            {"token": token_response.data["access"]},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)


class EncomiendaApiTests(ApiBaseTestCase):
    def test_listado_encomiendas_paginado(self):
        response = self.client.get("/api/v1/encomiendas/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("results", response.data)
        self.assertEqual(response["X-API-Version"], "v1")

    def test_crear_encomienda(self):
        response = self.client.post(
            "/api/v1/encomiendas/",
            {
                "codigo": "enc-api-002",
                "descripcion": "Nuevo paquete",
                "peso_kg": "1.50",
                "remitente_id": self.remitente.id,
                "destinatario_id": self.destinatario.id,
                "ruta_id": self.ruta.id,
                "costo_envio": "25.00",
                "fecha_entrega_est": str(timezone.now().date() + timedelta(days=3)),
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Encomienda.objects.filter(codigo="ENC-API-002").exists())

    def test_crear_encomienda_error_400(self):
        response = self.client.post(
            "/api/v1/encomiendas/",
            {
                "codigo": "ENC-API-003",
                "descripcion": "Destino invalido",
                "peso_kg": "1.50",
                "remitente_id": self.remitente.id,
                "destinatario_id": self.remitente.id,
                "ruta_id": self.ruta.id,
                "costo_envio": "25.00",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cambiar_estado(self):
        response = self.client.post(
            f"/api/v1/encomiendas/{self.encomienda.id}/cambiar_estado/",
            {"estado": EstadoEnvio.EN_TRANSITO, "observacion": "Salida a ruta"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.encomienda.refresh_from_db()
        self.assertEqual(self.encomienda.estado, EstadoEnvio.EN_TRANSITO)
        self.assertTrue(
            HistorialEstado.objects.filter(
                encomienda=self.encomienda,
                estado_nuevo=EstadoEnvio.EN_TRANSITO,
            ).exists()
        )

    def test_acciones_personalizadas(self):
        pendientes = self.client.get("/api/v1/encomiendas/pendientes/")
        estadisticas = self.client.get("/api/v1/encomiendas/estadisticas/")
        stats = self.client.get("/api/v2/encomiendas/stats/")

        self.assertEqual(pendientes.status_code, status.HTTP_200_OK)
        self.assertEqual(estadisticas.status_code, status.HTTP_200_OK)
        self.assertEqual(stats.status_code, status.HTTP_200_OK)
        self.assertIn("activas", estadisticas.data)

    def test_versionado_v2(self):
        response = self.client.get("/api/v2/encomiendas/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["X-API-Version"], "v2")
