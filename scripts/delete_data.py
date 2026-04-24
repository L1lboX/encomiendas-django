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
from envios.models import Encomienda


def delete_examples():
    try:
        enc = Encomienda.objects.get(codigo="ENC-2026-001")
        deleted_count, _ = enc.delete()
        print(f"Eliminacion individual: {deleted_count} registro(s)")
    except Encomienda.DoesNotExist:
        print("No existe la encomienda ENC-2026-001 para eliminar.")

    deleted_count, _ = Encomienda.objects.filter(
        estado=EstadoEnvio.DEVUELTO
    ).delete()
    print(f"Eliminacion por filtro: {deleted_count} registro(s)")


if __name__ == "__main__":
    delete_examples()
