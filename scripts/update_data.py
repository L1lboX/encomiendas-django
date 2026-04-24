from pathlib import Path
import os
import sys


BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django

django.setup()

from config.choices import EstadoEnvio
from envios.models import Empleado, Encomienda, HistorialEstado


def update_examples():
    try:
        enc = Encomienda.objects.get(codigo="ENC-2026-001")
        e1 = Empleado.objects.get(codigo="EMP001")
    except (Encomienda.DoesNotExist, Empleado.DoesNotExist):
        print(
            "Faltan datos de prueba. Ejecuta primero scripts/seed_data.py."
        )
        return

    estado_anterior = enc.estado
    enc.estado = EstadoEnvio.EN_TRANSITO
    enc.save()

    HistorialEstado.objects.create(
        encomienda=enc,
        estado_anterior=estado_anterior,
        estado_nuevo=EstadoEnvio.EN_TRANSITO,
        empleado=e1,
        observacion="Encomienda recogida y en camino a destino",
    )

    actualizados = Encomienda.objects.filter(
        estado=EstadoEnvio.PENDIENTE
    ).update(estado=EstadoEnvio.EN_TRANSITO)

    print(f"Encomienda actualizada: {enc.codigo} -> {enc.estado}")
    print(f"Registros actualizados con update(): {actualizados}")


if __name__ == "__main__":
    update_examples()
