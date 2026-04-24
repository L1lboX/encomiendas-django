from decimal import Decimal
from pathlib import Path
import os
import sys


BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django

django.setup()

from clientes.models import Cliente
from config.choices import EstadoEnvio
from envios.models import Empleado, Encomienda, HistorialEstado
from rutas.models import Ruta


def run_demo():
    try:
        enc = Encomienda.objects.get(codigo="ENC-2026-001")
        e1 = Empleado.objects.get(codigo="EMP001")
        c2 = Cliente.objects.get(nro_doc="87654321")
        r1 = Ruta.objects.get(codigo="LIM-TRU")
    except (
        Encomienda.DoesNotExist,
        Empleado.DoesNotExist,
        Cliente.DoesNotExist,
        Ruta.DoesNotExist,
    ):
        print("Faltan datos de prueba. Ejecuta primero scripts/seed_data.py.")
        return

    if enc.estado != EstadoEnvio.EN_TRANSITO:
        enc.cambiar_estado(
            nuevo_estado=EstadoEnvio.EN_TRANSITO,
            empleado=e1,
            observacion="Encomienda recogida en agencia Lima",
        )
    else:
        print("ENC-2026-001 ya estaba en transito; no se repite el cambio.")

    print(enc.estado)
    print(enc.esta_en_transito)
    print(enc.dias_en_transito)
    print(enc.tiene_retraso)
    print(list(enc.historial.all()))

    c1 = enc.remitente
    print(c1.nombre_completo)
    print(c1.total_encomiendas_enviadas)
    print(c1.esta_activo)

    nueva = Encomienda.crear_con_costo_calculado(
        remitente=c1,
        destinatario=c2,
        ruta=r1,
        empleado=e1,
        descripcion="Zapatos y ropa de niño",
        peso_kg=Decimal("7.0"),
    )
    print(nueva.codigo)
    print(nueva.costo_envio)

    historial_reciente = HistorialEstado.objects.filter(encomienda=enc)
    print(list(historial_reciente))


if __name__ == "__main__":
    run_demo()
