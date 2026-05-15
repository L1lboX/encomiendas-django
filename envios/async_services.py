import asyncio

import httpx
from asgiref.sync import sync_to_async
from django.utils import timezone

from config.choices import EstadoEnvio
from .models import Encomienda


async def verificar_estado_transportista(codigo: str) -> dict:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.transportista.pe/track/{codigo}",
                timeout=5.0,
            )
            response.raise_for_status()
            data = response.json()
            return {
                "codigo": codigo,
                "found": True,
                "status": data.get("status"),
                "location": data.get("location"),
                "timestamp": timezone.now().isoformat(),
            }
    except httpx.TimeoutException:
        return {"codigo": codigo, "found": False, "error": "timeout"}
    except httpx.HTTPError as exc:
        return {"codigo": codigo, "found": False, "error": str(exc)}


async def actualizar_estados_en_transito() -> list:
    encomiendas = await _alist(Encomienda.objects.en_transito())
    tareas = [verificar_estado_transportista(enc.codigo) for enc in encomiendas]
    resultados = await asyncio.gather(*tareas, return_exceptions=True)

    actualizadas = []
    for enc, resultado in zip(encomiendas, resultados, strict=False):
        if isinstance(resultado, dict) and resultado.get("status") == "delivered":
            enc.estado = EstadoEnvio.ENTREGADO
            enc.fecha_entrega_real = timezone.now().date()
            await enc.asave()
            actualizadas.append(enc.codigo)

    return actualizadas


async def verificar_una(session: httpx.AsyncClient, codigo: str) -> dict:
    try:
        response = await session.get(
            f"https://api.transportista.pe/track/{codigo}",
            timeout=5.0,
        )
        return {"codigo": codigo, "ok": True, "data": response.json()}
    except httpx.TimeoutException:
        return {"codigo": codigo, "ok": False, "error": "timeout"}
    except Exception as exc:
        return {"codigo": codigo, "ok": False, "error": str(exc)}


async def verificar_lote_completo() -> dict:
    encomiendas = await _alist(Encomienda.objects.en_transito())
    if not encomiendas:
        return {"verificadas": 0, "resultados": []}

    async with httpx.AsyncClient() as session:
        tareas = [verificar_una(session, enc.codigo) for enc in encomiendas]
        resultados = await asyncio.gather(*tareas, return_exceptions=True)

    exitosas = [r for r in resultados if isinstance(r, dict) and r.get("ok")]
    fallidas = [r for r in resultados if isinstance(r, dict) and not r.get("ok")]
    errores = [r for r in resultados if isinstance(r, Exception)]

    return {
        "verificadas": len(encomiendas),
        "exitosas": len(exitosas),
        "fallidas": len(fallidas),
        "errores": len(errores),
        "resultados": resultados,
    }


async def verificar_con_timeout(enc: Encomienda) -> dict:
    try:
        return await asyncio.wait_for(
            verificar_estado_transportista(enc.codigo),
            timeout=3.0,
        )
    except asyncio.TimeoutError:
        return {"codigo": enc.codigo, "found": False, "error": "timeout"}


async def verificar_lote_con_timeout(codigos: list[str]) -> list[dict]:
    async with httpx.AsyncClient() as session:
        tareas = [
            asyncio.wait_for(verificar_una(session, codigo), timeout=3.0)
            for codigo in codigos
        ]
        resultados = await asyncio.gather(*tareas, return_exceptions=True)

    normalizados = []
    for codigo, resultado in zip(codigos, resultados, strict=False):
        if isinstance(resultado, asyncio.TimeoutError):
            normalizados.append({"codigo": codigo, "ok": False, "error": "timeout"})
        elif isinstance(resultado, Exception):
            normalizados.append({"codigo": codigo, "ok": False, "error": str(resultado)})
        else:
            normalizados.append(resultado)
    return normalizados


async def _alist(queryset):
    return await sync_to_async(list)(queryset)
