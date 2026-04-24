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
from rutas.models import Ruta


def lookup_examples():
    print(
        "Estado exacto EN_TRANSITO:",
        list(Encomienda.objects.filter(estado__exact=EstadoEnvio.EN_TRANSITO)),
    )
    print(
        "Destino iexact trujillo:",
        list(Ruta.objects.filter(destino__iexact="trujillo")),
    )
    print(
        "Descripcion contains caja:",
        list(Encomienda.objects.filter(descripcion__contains="caja")),
    )
    print(
        "Descripcion icontains Caja:",
        list(Encomienda.objects.filter(descripcion__icontains="Caja")),
    )
    print(
        "Estado in [PE, TR]:",
        list(
            Encomienda.objects.filter(
                estado__in=[
                    EstadoEnvio.PENDIENTE,
                    EstadoEnvio.EN_TRANSITO,
                ]
            )
        ),
    )
    print(
        "Peso >= 5:",
        list(Encomienda.objects.filter(peso_kg__gte=5)),
    )
    print(
        "Costo <= 30:",
        list(Encomienda.objects.filter(costo_envio__lte=30)),
    )
    print(
        "Remitente con DNI 12345678:",
        list(Encomienda.objects.filter(remitente__nro_doc="12345678")),
    )
    print(
        "Ruta LIM-TRU:",
        list(Encomienda.objects.filter(ruta__codigo="LIM-TRU")),
    )


if __name__ == "__main__":
    lookup_examples()
