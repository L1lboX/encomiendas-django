from datetime import timedelta
from pathlib import Path
import os
import sys


BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django

django.setup()

from django.core.exceptions import ValidationError
from django.utils import timezone

from clientes.models import Cliente
from envios.models import Empleado, Encomienda
from rutas.models import Ruta


def run_lab():
    try:
        c1 = Cliente.objects.get(nro_doc="12345678")
        r1 = Ruta.objects.get(codigo="LIM-TRU")
        e1 = Empleado.objects.get(codigo="EMP001")
    except (Cliente.DoesNotExist, Ruta.DoesNotExist, Empleado.DoesNotExist):
        print("Faltan datos de prueba. Ejecuta primero scripts/seed_data.py.")
        return

    try:
        enc = Encomienda(
            codigo="ENC-2026-002",
            descripcion="Prueba",
            peso_kg=-1,
            remitente=c1,
            destinatario=c1,
            ruta=r1,
            empleado_registro=e1,
            costo_envio=25,
            fecha_entrega_est=timezone.now().date() - timedelta(days=1),
        )
        enc.save()
    except ValidationError as exc:
        print("Errores encontrados:")
        for campo, mensajes in exc.message_dict.items():
            print(f"  [{campo}]: {mensajes}")


if __name__ == "__main__":
    run_lab()
