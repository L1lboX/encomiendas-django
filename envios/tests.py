from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from clientes.models import Cliente
from config.choices import EstadoEnvio, EstadoGeneral, TipoDocumento
from envios.models import Empleado, Encomienda, HistorialEstado
from rutas.models import Ruta


class BaseModelTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
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
        cls.cliente_baja = Cliente.objects.create(
            tipo_doc=TipoDocumento.RUC,
            nro_doc="20123456789",
            nombres="Empresa",
            apellidos="Logistica",
            estado=EstadoGeneral.DE_BAJA,
        )
        cls.ruta_lima = Ruta.objects.create(
            codigo="LIM-TRU",
            origen="Lima",
            destino="Trujillo",
            precio_base=Decimal("20.00"),
            dias_entrega=2,
            estado=EstadoGeneral.ACTIVO,
        )
        cls.ruta_inactiva = Ruta.objects.create(
            codigo="LIM-ARE",
            origen="Lima",
            destino="Arequipa",
            precio_base=Decimal("30.00"),
            dias_entrega=3,
            estado=EstadoGeneral.DE_BAJA,
        )
        cls.empleado = Empleado.objects.create(
            codigo="EMP001",
            nombres="Lucia",
            apellidos="Perez",
            cargo="Operador",
            email="lucia@example.com",
            estado=EstadoGeneral.ACTIVO,
            fecha_ingreso=timezone.now().date(),
        )

        manana = timezone.now().date() + timedelta(days=1)
        dos_dias = timezone.now().date() + timedelta(days=2)

        cls.encomienda_pendiente = Encomienda.objects.create(
            codigo="ENC-TEST-001",
            descripcion="Caja con ropa",
            peso_kg=Decimal("3.50"),
            remitente=cls.remitente,
            destinatario=cls.destinatario,
            ruta=cls.ruta_lima,
            empleado_registro=cls.empleado,
            estado=EstadoEnvio.PENDIENTE,
            costo_envio=Decimal("20.00"),
            fecha_entrega_est=dos_dias,
        )
        cls.encomienda_transito = Encomienda.objects.create(
            codigo="ENC-TEST-002",
            descripcion="Documentos urgentes",
            peso_kg=Decimal("2.00"),
            remitente=cls.remitente,
            destinatario=cls.destinatario,
            ruta=cls.ruta_lima,
            empleado_registro=cls.empleado,
            estado=EstadoEnvio.EN_TRANSITO,
            costo_envio=Decimal("20.00"),
            fecha_entrega_est=manana,
        )
        cls.encomienda_entregada = Encomienda.objects.create(
            codigo="ENC-TEST-003",
            descripcion="Paquete entregado correctamente",
            peso_kg=Decimal("1.00"),
            remitente=cls.destinatario,
            destinatario=cls.remitente,
            ruta=cls.ruta_lima,
            empleado_registro=cls.empleado,
            estado=EstadoEnvio.ENTREGADO,
            costo_envio=Decimal("20.00"),
            fecha_entrega_est=manana,
            fecha_entrega_real=manana,
        )


class EncomiendaValidationTests(BaseModelTestCase):
    def test_clean_rechaza_mismo_remitente_y_destinatario(self):
        encomienda = Encomienda(
            codigo="ENC-TEST-004",
            descripcion="Paquete invalido",
            peso_kg=Decimal("1.00"),
            remitente=self.remitente,
            destinatario=self.remitente,
            ruta=self.ruta_lima,
            empleado_registro=self.empleado,
            costo_envio=Decimal("20.00"),
            fecha_entrega_est=timezone.now().date() + timedelta(days=1),
        )

        with self.assertRaises(ValidationError) as exc:
            encomienda.clean()

        self.assertIn("destinatario", exc.exception.message_dict)

    def test_clean_rechaza_fecha_estimada_en_pasado(self):
        encomienda = Encomienda(
            codigo="ENC-TEST-005",
            descripcion="Paquete invalido",
            peso_kg=Decimal("1.00"),
            remitente=self.remitente,
            destinatario=self.destinatario,
            ruta=self.ruta_lima,
            empleado_registro=self.empleado,
            costo_envio=Decimal("20.00"),
            fecha_entrega_est=timezone.now().date() - timedelta(days=1),
        )

        with self.assertRaises(ValidationError) as exc:
            encomienda.clean()

        self.assertIn("fecha_entrega_est", exc.exception.message_dict)

    def test_clean_rechaza_fecha_real_antes_de_estimacion(self):
        manana = timezone.now().date() + timedelta(days=1)
        encomienda = Encomienda(
            codigo="ENC-TEST-006",
            descripcion="Paquete invalido",
            peso_kg=Decimal("1.00"),
            remitente=self.remitente,
            destinatario=self.destinatario,
            ruta=self.ruta_lima,
            empleado_registro=self.empleado,
            costo_envio=Decimal("20.00"),
            fecha_entrega_est=manana,
            fecha_entrega_real=timezone.now().date(),
        )

        with self.assertRaises(ValidationError) as exc:
            encomienda.clean()

        self.assertIn("fecha_entrega_real", exc.exception.message_dict)

    def test_save_llama_full_clean(self):
        encomienda = Encomienda(
            codigo="ENC-TEST-007",
            descripcion="Paquete invalido",
            peso_kg=Decimal("-1.00"),
            remitente=self.remitente,
            destinatario=self.destinatario,
            ruta=self.ruta_lima,
            empleado_registro=self.empleado,
            costo_envio=Decimal("20.00"),
            fecha_entrega_est=timezone.now().date() + timedelta(days=1),
        )

        with self.assertRaises(ValidationError):
            encomienda.save()


class ClientePropertiesTests(BaseModelTestCase):
    def test_nombre_completo(self):
        self.assertEqual(
            self.remitente.nombre_completo,
            "Ramirez, Carlos",
        )

    def test_esta_activo(self):
        self.assertTrue(self.remitente.esta_activo)
        self.assertFalse(self.cliente_baja.esta_activo)

    def test_total_encomiendas_enviadas(self):
        self.assertEqual(self.remitente.total_encomiendas_enviadas, 2)


class EncomiendaPropertiesAndMethodsTests(BaseModelTestCase):
    def test_propiedades_de_encomienda(self):
        self.assertFalse(self.encomienda_pendiente.esta_entregada)
        self.assertFalse(self.encomienda_pendiente.tiene_retraso)
        self.assertGreaterEqual(self.encomienda_pendiente.dias_en_transito, 0)
        self.assertEqual(
            self.encomienda_pendiente.descripcion_corta,
            "Caja con ropa",
        )

    def test_tiene_retraso_cuando_fecha_estimacion_ya_paso(self):
        ayer = timezone.now().date() - timedelta(days=1)
        Encomienda.objects.filter(pk=self.encomienda_transito.pk).update(
            fecha_entrega_est=ayer
        )
        self.encomienda_transito.refresh_from_db()

        self.assertTrue(self.encomienda_transito.tiene_retraso)

    def test_cambiar_estado_actualiza_y_crea_historial(self):
        self.encomienda_pendiente.cambiar_estado(
            nuevo_estado=EstadoEnvio.ENTREGADO,
            empleado=self.empleado,
            observacion="Entrega completada",
        )
        self.encomienda_pendiente.refresh_from_db()

        self.assertEqual(self.encomienda_pendiente.estado, EstadoEnvio.ENTREGADO)
        self.assertIsNotNone(self.encomienda_pendiente.fecha_entrega_real)
        self.assertTrue(
            HistorialEstado.objects.filter(
                encomienda=self.encomienda_pendiente,
                estado_anterior=EstadoEnvio.PENDIENTE,
                estado_nuevo=EstadoEnvio.ENTREGADO,
            ).exists()
        )

    def test_crear_con_costo_calculado(self):
        encomienda = Encomienda.crear_con_costo_calculado(
            remitente=self.remitente,
            destinatario=self.destinatario,
            ruta=self.ruta_lima,
            empleado=self.empleado,
            descripcion="Carga pesada",
            peso_kg=Decimal("7.00"),
        )

        self.assertTrue(encomienda.codigo.startswith("ENC-"))
        self.assertEqual(encomienda.costo_envio, Decimal("25.00"))
        self.assertEqual(
            encomienda.fecha_entrega_est,
            timezone.now().date() + timedelta(days=self.ruta_lima.dias_entrega),
        )


class CustomManagerTests(BaseModelTestCase):
    def test_encomienda_queryset_methods(self):
        ayer = timezone.now().date() - timedelta(days=1)
        Encomienda.objects.filter(pk=self.encomienda_transito.pk).update(
            fecha_entrega_est=ayer
        )

        self.assertEqual(Encomienda.objects.pendientes().count(), 1)
        self.assertEqual(Encomienda.objects.activas().count(), 2)
        self.assertEqual(Encomienda.objects.con_retraso().count(), 1)

    def test_cliente_queryset_methods(self):
        self.assertEqual(Cliente.objects.activos().count(), 2)
        self.assertEqual(Cliente.objects.buscar("rami").count(), 1)
        self.assertEqual(Cliente.objects.con_dni().count(), 2)

    def test_ruta_queryset_methods(self):
        self.assertEqual(Ruta.objects.activas().count(), 1)
        self.assertEqual(Ruta.objects.activas().por_origen("Lima").count(), 1)

    def test_encadenamiento_por_ruta(self):
        total = Encomienda.objects.activas().por_ruta(self.ruta_lima).count()
        self.assertEqual(total, 2)

    def test_con_relaciones_hace_select_related(self):
        queryset = Encomienda.objects.activas().con_relaciones()

        self.assertIn("remitente", queryset.query.select_related)
        self.assertIn("destinatario", queryset.query.select_related)
        self.assertIn("ruta", queryset.query.select_related)
        self.assertIn("empleado_registro", queryset.query.select_related)
