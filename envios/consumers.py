import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.utils import timezone

from config.choices import EstadoEnvio
from .models import Encomienda


class EncomiendaConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope["user"]
        if not user.is_authenticated:
            await self.close(code=4001)
            return

        self.group_name = "encomiendas_global"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        stats = await self.get_estadisticas()
        await self.send_json(
            {
                "tipo": "conectado",
                "mensaje": f"Bienvenido, {user.username}",
                "usuario": user.username,
                "stats": stats,
            }
        )

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            await self.procesar_mensaje(data)
        except json.JSONDecodeError:
            await self.send_json(
                {
                    "tipo": "error",
                    "codigo": "JSON_INVALIDO",
                    "mensaje": "El mensaje no es JSON valido",
                }
            )
        except Exception:
            await self.send_json(
                {
                    "tipo": "error",
                    "codigo": "ERROR_INTERNO",
                    "mensaje": "Error interno del servidor",
                }
            )

    async def procesar_mensaje(self, data):
        tipo = data.get("tipo")
        if tipo == "ping":
            await self.send_json({"tipo": "pong"})
        elif tipo == "solicitar_stats":
            stats = await self.get_estadisticas()
            await self.send_json({"tipo": "stats", "stats": stats})
        elif tipo == "suscribir_encomienda":
            enc_id = data.get("encomienda_id")
            if enc_id:
                await self.channel_layer.group_add(f"encomienda_{enc_id}", self.channel_name)
                await self.send_json(
                    {
                        "tipo": "suscrito",
                        "encomienda_id": enc_id,
                    }
                )

    async def encomienda_estado_cambio(self, event):
        await self.send_json(
            {
                "tipo": "estado_cambio",
                "encomienda_id": event["encomienda_id"],
                "codigo": event["codigo"],
                "estado_anterior": event["estado_anterior"],
                "estado_nuevo": event["estado_nuevo"],
                "empleado": event["empleado"],
                "timestamp": event["timestamp"],
            }
        )

    async def bulk_create_progreso(self, event):
        await self.send_json(
            {
                "tipo": "progreso",
                "actual": event["actual"],
                "total": event["total"],
                "codigo": event.get("codigo"),
            }
        )

    @database_sync_to_async
    def get_estadisticas(self):
        return calcular_stats()

    async def send_json(self, content):
        await self.send(text_data=json.dumps(content))


class EncomiendaDetalleConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope["user"]
        if not user.is_authenticated:
            await self.close(code=4001)
            return

        self.enc_pk = self.scope["url_route"]["kwargs"]["pk"]
        self.group_name = f"encomienda_{self.enc_pk}"

        existe = await self.enc_existe(self.enc_pk)
        if not existe:
            await self.close(code=4004)
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        estado = await self.get_estado_actual(self.enc_pk)
        await self.send_json({"tipo": "estado_actual", "encomienda": estado})

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            await self.send_json({"tipo": "error", "codigo": "JSON_INVALIDO"})
            return

        if data.get("tipo") == "ping":
            await self.send_json({"tipo": "pong"})

    async def encomienda_estado_cambio(self, event):
        await self.send_json(
            {
                "tipo": "estado_cambio",
                "encomienda_id": event["encomienda_id"],
                "codigo": event["codigo"],
                "estado_anterior": event["estado_anterior"],
                "estado_nuevo": event["estado_nuevo"],
                "empleado": event["empleado"],
                "timestamp": event["timestamp"],
            }
        )

    @database_sync_to_async
    def enc_existe(self, pk):
        return Encomienda.objects.filter(pk=pk).exists()

    @database_sync_to_async
    def get_estado_actual(self, pk):
        enc = Encomienda.objects.get(pk=pk)
        return {
            "id": enc.pk,
            "codigo": enc.codigo,
            "estado": enc.estado,
            "estado_display": enc.get_estado_display(),
        }

    async def send_json(self, content):
        await self.send(text_data=json.dumps(content))


class DashboardConsumer(AsyncWebsocketConsumer):
    group_name = "dashboard"

    async def connect(self):
        user = self.scope["user"]
        if not user.is_authenticated:
            await self.close(code=4001)
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        stats = await self.get_stats()
        await self.send_json({"tipo": "stats_iniciales", "stats": stats})

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            await self.send_json({"tipo": "error", "codigo": "JSON_INVALIDO"})
            return

        if data.get("tipo") == "ping":
            await self.send_json({"tipo": "pong"})
        elif data.get("tipo") == "solicitar_stats":
            stats = await self.get_stats()
            await self.send_json({"tipo": "stats_actualizado", "stats": stats})

    async def dashboard_actualizar(self, event):
        await self.send_json(
            {
                "tipo": "stats_actualizado",
                "stats": event["stats"],
                "evento": event.get("evento"),
            }
        )

    async def bulk_create_progreso(self, event):
        await self.send_json(
            {
                "tipo": "progreso",
                "actual": event["actual"],
                "total": event["total"],
                "codigo": event.get("codigo"),
            }
        )

    @database_sync_to_async
    def get_stats(self):
        return calcular_stats()

    async def send_json(self, content):
        await self.send(text_data=json.dumps(content))


def calcular_stats():
    hoy = timezone.now().date()
    return {
        "activas": Encomienda.objects.activas().count(),
        "en_transito": Encomienda.objects.en_transito().count(),
        "con_retraso": Encomienda.objects.con_retraso().count(),
        "entregadas_hoy": Encomienda.objects.filter(
            estado=EstadoEnvio.ENTREGADO,
            fecha_entrega_real=hoy,
        ).count(),
    }
