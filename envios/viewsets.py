from django.core.cache import cache
from django.db.models import Q
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_headers
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response

from clientes.models import Cliente
from config.settings import CACHE_TTL
from rutas.models import Ruta
from api.filters import EncomiendaFilter
from api.pagination import ClientePagination, EncomiendaPagination, HistorialPagination
from api.permissions import EsEmpleadoActivo, EsPropietarioOAdmin
from api.throttles import CambioEstadoThrottle, EmpleadoRateThrottle
from .models import Empleado, Encomienda, HistorialEstado
from .serializers import (
    ClienteSerializer,
    EncomiendaDetailSerializer,
    EncomiendaListSerializer,
    EncomiendaSerializer,
    EncomiendaV2Serializer,
    HistorialEstadoSerializer,
    RutaSerializer,
)


def empleado_para_usuario(user):
    return Empleado.objects.filter(email=user.email).first()


@extend_schema_view(
    list=extend_schema(summary="Listar encomiendas", tags=["Encomiendas"]),
    retrieve=extend_schema(summary="Detalle de encomienda", tags=["Encomiendas"]),
    create=extend_schema(summary="Crear encomienda", tags=["Encomiendas"]),
    update=extend_schema(summary="Actualizar encomienda", tags=["Encomiendas"]),
    partial_update=extend_schema(summary="Actualizar parcialmente encomienda", tags=["Encomiendas"]),
    destroy=extend_schema(summary="Eliminar encomienda", tags=["Encomiendas"]),
)
class EncomiendaViewSet(viewsets.ModelViewSet):
    queryset = Encomienda.objects.con_relaciones()
    pagination_class = EncomiendaPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = EncomiendaFilter
    search_fields = [
        "codigo",
        "remitente__apellidos",
        "remitente__nombres",
        "destinatario__apellidos",
        "destinatario__nombres",
        "ruta__origen",
        "ruta__destino",
    ]
    ordering_fields = [
        "fecha_registro",
        "fecha_entrega_est",
        "peso_kg",
        "costo_envio",
    ]
    ordering = ["-fecha_registro"]
    throttle_classes = [EmpleadoRateThrottle]

    def get_permissions(self):
        if self.action in ["update", "partial_update", "destroy"]:
            return [EsEmpleadoActivo(), EsPropietarioOAdmin()]
        return [EsEmpleadoActivo()]

    def get_throttles(self):
        if self.action == "cambiar_estado":
            return [CambioEstadoThrottle()]
        return super().get_throttles()

    def get_serializer_class(self):
        version = getattr(self.request, "version", "v1")
        if version == "v2":
            return EncomiendaV2Serializer
        if self.action == "list":
            return EncomiendaListSerializer
        if self.action in ["retrieve", "historial"]:
            return EncomiendaDetailSerializer
        return EncomiendaSerializer

    def get_queryset(self):
        qs = Encomienda.objects.con_relaciones()

        if self.action == "list":
            qs = qs.only(
                "id",
                "codigo",
                "estado",
                "peso_kg",
                "costo_envio",
                "fecha_registro",
                "fecha_entrega_est",
                "remitente_id",
                "destinatario_id",
                "ruta_id",
                "empleado_registro_id",
                "remitente__nombres",
                "remitente__apellidos",
                "destinatario__nombres",
                "destinatario__apellidos",
                "ruta__destino",
                "empleado_registro__email",
                "empleado_registro__apellidos",
            )

        estado = self.request.query_params.get("estado")
        if estado:
            qs = qs.filter(estado=estado)

        q = self.request.query_params.get("search")
        if q:
            qs = qs.filter(
                Q(codigo__icontains=q)
                | Q(remitente__apellidos__icontains=q)
                | Q(destinatario__apellidos__icontains=q)
            )
        return qs

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        response["X-API-Version"] = getattr(request, "version", "v1")
        return response

    def retrieve(self, request, *args, **kwargs):
        response = super().retrieve(request, *args, **kwargs)
        response["X-API-Version"] = getattr(request, "version", "v1")
        return response

    def perform_create(self, serializer):
        serializer.save(empleado_registro=empleado_para_usuario(self.request.user))

    @extend_schema(
        summary="Cambiar estado de encomienda",
        parameters=[
            OpenApiParameter("estado", OpenApiTypes.STR, OpenApiParameter.QUERY),
        ],
        tags=["Encomiendas"],
    )
    @action(detail=True, methods=["post"], url_path="cambiar_estado")
    def cambiar_estado(self, request, pk=None, **kwargs):
        enc = self.get_object()
        nuevo_estado = request.data.get("estado")
        observacion = request.data.get("observacion", "")

        if not nuevo_estado:
            return Response(
                {"error": "El campo estado es requerido."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            enc.cambiar_estado(nuevo_estado, empleado_para_usuario(request.user), observacion)
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(EncomiendaSerializer(enc, context={"request": request}).data)

    @extend_schema(summary="Encomiendas con retraso", tags=["Encomiendas"])
    @action(detail=False, methods=["get"], url_path="con_retraso")
    def con_retraso(self, request, **kwargs):
        qs = Encomienda.objects.con_retraso().con_relaciones()
        page = self.paginate_queryset(qs)
        if page is not None:
            return self.get_paginated_response(
                EncomiendaListSerializer(page, many=True, context={"request": request}).data
            )
        return Response(EncomiendaListSerializer(qs, many=True, context={"request": request}).data)

    @extend_schema(summary="Encomiendas pendientes", tags=["Encomiendas"])
    @action(detail=False, methods=["get"])
    def pendientes(self, request, **kwargs):
        qs = Encomienda.objects.pendientes().con_relaciones()
        page = self.paginate_queryset(qs)
        if page is not None:
            return self.get_paginated_response(
                EncomiendaListSerializer(page, many=True, context={"request": request}).data
            )
        return Response(EncomiendaListSerializer(qs, many=True, context={"request": request}).data)

    @extend_schema(summary="Historial de una encomienda", tags=["Encomiendas"])
    @action(detail=True, methods=["get"])
    def historial(self, request, pk=None, **kwargs):
        enc = self.get_object()
        qs = enc.historial.select_related("empleado")
        paginator = HistorialPagination()
        page = paginator.paginate_queryset(qs, request)
        serializer = HistorialEstadoSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @extend_schema(summary="Estadisticas de encomiendas", tags=["Encomiendas"])
    @action(detail=False, methods=["get"], url_path="estadisticas")
    def estadisticas(self, request, **kwargs):
        cache_key = f"estadisticas_empleado_{request.user.id}"
        data = cache.get(cache_key)
        if data is None:
            data = {
                "activas": Encomienda.objects.activas().count(),
                "en_transito": Encomienda.objects.en_transito().count(),
                "con_retraso": Encomienda.objects.con_retraso().count(),
                "entregadas_mes": Encomienda.objects.filter(
                    estado="EN",
                    fecha_entrega_real__month=timezone.now().month,
                ).count(),
            }
            cache.set(cache_key, data, CACHE_TTL)
        return Response(data)

    @extend_schema(summary="Stats de encomiendas v2", tags=["Encomiendas"])
    @action(detail=False, methods=["get"], url_path="stats")
    def stats(self, request, **kwargs):
        return self.estadisticas(request, **kwargs)

    def perform_update(self, serializer):
        super().perform_update(serializer)
        cache.delete(f"estadisticas_empleado_{self.request.user.id}")

    @extend_schema(summary="Crear multiples encomiendas", tags=["Encomiendas"])
    @action(detail=False, methods=["post"], url_path="bulk_create")
    def bulk_create(self, request, **kwargs):
        serializer = EncomiendaSerializer(
            data=request.data,
            many=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        empleado = empleado_para_usuario(request.user)
        total = len(serializer.validated_data)
        creadas = []

        for actual, item in enumerate(serializer.validated_data, start=1):
            encomienda = Encomienda.objects.create(
                empleado_registro=empleado,
                **item,
            )
            creadas.append(encomienda)
            self._notificar_bulk_create(actual, total, encomienda.codigo)

        data = EncomiendaSerializer(creadas, many=True, context={"request": request}).data
        return Response(data, status=status.HTTP_201_CREATED)

    def _notificar_bulk_create(self, actual, total, codigo):
        try:
            from asgiref.sync import async_to_sync
            from channels.layers import get_channel_layer

            channel_layer = get_channel_layer()
            evento = {
                "type": "bulk.create.progreso",
                "actual": actual,
                "total": total,
                "codigo": codigo,
            }
            async_to_sync(channel_layer.group_send)("encomiendas_global", evento)
            async_to_sync(channel_layer.group_send)("dashboard", evento)
        except Exception:
            return

    @extend_schema(summary="Cambiar estado en lote", tags=["Encomiendas"])
    @action(detail=False, methods=["patch"], url_path="bulk_estado")
    def bulk_estado(self, request, **kwargs):
        ids = request.data.get("ids", [])
        nuevo_estado = request.data.get("estado")
        observacion = request.data.get("observacion", "")

        if not ids:
            return Response(
                {"error": "El campo ids es requerido y no puede estar vacio."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not nuevo_estado:
            return Response(
                {"error": "El campo estado es requerido."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        actualizadas = []
        errores = []
        no_encontrados = []
        empleado = empleado_para_usuario(request.user)

        encomiendas = {enc.id: enc for enc in Encomienda.objects.filter(id__in=ids)}
        for enc_id in ids:
            enc = encomiendas.get(enc_id)
            if not enc:
                no_encontrados.append(enc_id)
                continue
            try:
                enc.cambiar_estado(nuevo_estado, empleado, observacion)
            except ValueError as exc:
                errores.append({"id": enc_id, "error": str(exc)})
            else:
                actualizadas.append(enc_id)

        cache.delete(f"estadisticas_empleado_{request.user.id}")
        return Response(
            {
                "actualizadas": actualizadas,
                "errores": errores,
                "no_encontrados": no_encontrados,
                "total": len(ids),
            }
        )


class ClienteViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ClienteSerializer
    pagination_class = ClientePagination
    permission_classes = [EsEmpleadoActivo]

    def get_queryset(self):
        return Cliente.objects.activos()


class RutaViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = RutaSerializer
    pagination_class = None
    permission_classes = [EsEmpleadoActivo]

    def get_queryset(self):
        return Ruta.objects.activas()

    @method_decorator(cache_page(CACHE_TTL))
    @method_decorator(vary_on_headers("Authorization"))
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class HistorialEstadoViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = HistorialEstado.objects.select_related("encomienda", "empleado")
    serializer_class = HistorialEstadoSerializer
    pagination_class = HistorialPagination
    permission_classes = [EsEmpleadoActivo]
