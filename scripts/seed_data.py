from datetime import date, timedelta
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
from envios.models import Empleado, Encomienda
from rutas.models import Ruta


def seed():
    c1, _ = Cliente.objects.update_or_create(
        nro_doc="12345678",
        defaults={
            "tipo_doc": "DNI",
            "nombres": "Carlos",
            "apellidos": "Ramirez Torres",
            "telefono": "987654321",
            "email": "carlos@mail.com",
        },
    )

    c2, _ = Cliente.objects.update_or_create(
        nro_doc="87654321",
        defaults={
            "tipo_doc": "DNI",
            "nombres": "Ana",
            "apellidos": "Flores Diaz",
            "telefono": "912345678",
        },
    )

    r1, _ = Ruta.objects.update_or_create(
        codigo="LIM-TRU",
        defaults={
            "origen": "Lima",
            "destino": "Trujillo",
            "precio_base": Decimal("25.00"),
            "dias_entrega": 2,
        },
    )

    e1, _ = Empleado.objects.update_or_create(
        codigo="EMP001",
        defaults={
            "nombres": "Luis",
            "apellidos": "Mendoza Cruz",
            "cargo": "Operador de envios",
            "email": "luis@encomiendas.pe",
            "fecha_ingreso": date.today(),
        },
    )
    e1.rutas_asignadas.add(r1)

    fecha_estimada = date.today() + timedelta(days=r1.dias_entrega)
    enc, _ = Encomienda.objects.update_or_create(
        codigo="ENC-2026-001",
        defaults={
            "descripcion": "Caja con ropa y documentos",
            "peso_kg": Decimal("3.50"),
            "remitente": c1,
            "destinatario": c2,
            "ruta": r1,
            "empleado_registro": e1,
            "costo_envio": r1.precio_base,
            "fecha_entrega_est": fecha_estimada,
        },
    )

    print(f"Cliente remitente: {c1}")
    print(f"Cliente destinatario: {c2}")
    print(f"Ruta: {r1}")
    print(f"Empleado: {e1}")
    print(f"Encomienda: {enc}")


if __name__ == "__main__":
    seed()
