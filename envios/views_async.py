import asyncio

from django.http import JsonResponse
from django.utils import timezone

from config.choices import EstadoEnvio
from .models import Encomienda


async def dashboard_stats_async(request):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "No autorizado"}, status=401)

    activas, en_transito, con_retraso, entregadas_hoy = await asyncio.gather(
        Encomienda.objects.activas().acount(),
        Encomienda.objects.en_transito().acount(),
        Encomienda.objects.con_retraso().acount(),
        Encomienda.objects.filter(
            estado=EstadoEnvio.ENTREGADO,
            fecha_entrega_real=timezone.now().date(),
        ).acount(),
    )

    return JsonResponse(
        {
            "activas": activas,
            "en_transito": en_transito,
            "con_retraso": con_retraso,
            "entregadas_hoy": entregadas_hoy,
        }
    )
