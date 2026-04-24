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
from envios.models import Encomienda
from rutas.models import Ruta


def query_examples():
    try:
        enc = Encomienda.objects.get(codigo="ENC-2026-001")
        ruta = Ruta.objects.get(codigo="LIM-TRU")
        cliente = Cliente.objects.get(nro_doc="12345678")
    except Encomienda.DoesNotExist:
        print(
            "No existe la encomienda ENC-2026-001. "
            "Ejecuta primero scripts/seed_data.py."
        )
        return
    except (Ruta.DoesNotExist, Cliente.DoesNotExist):
        print("Faltan datos de prueba. Ejecuta primero scripts/seed_data.py.")
        return

    print("Encomiendas pendientes:", list(Encomienda.objects.pendientes()))
    print("Encomiendas en transito:", list(Encomienda.objects.en_transito()))
    print("Encomiendas con retraso:", list(Encomienda.objects.con_retraso()))
    print("Clientes activos:", list(Cliente.objects.activos()))
    print("Rutas activas desde Lima:", list(Ruta.objects.activas().por_origen("Lima")))

    print("Remitente:", enc.remitente)
    print("Nombre del remitente:", enc.remitente.nombres)
    print("Destino de la ruta:", enc.ruta.destino)

    print(
        "Encomiendas activas del cliente en la ruta:",
        list(Encomienda.objects.activas().por_remitente(cliente).por_ruta(ruta)),
    )
    print(
        "En transito por ruta:",
        list(Encomienda.objects.en_transito_por_ruta(ruta)),
    )
    print("Busqueda de clientes 'rami':", list(Cliente.objects.buscar("rami")))
    print("Clientes activos con DNI:", list(Cliente.objects.activos().con_dni()))
    print("Pendientes count:", Encomienda.objects.pendientes().count())
    print("Con retraso count:", Encomienda.objects.con_retraso().count())

    encomiendas = Encomienda.objects.activas().con_relaciones()
    for item in encomiendas:
        print(item.remitente.nombre_completo, "->", item.ruta.destino)


if __name__ == "__main__":
    query_examples()
