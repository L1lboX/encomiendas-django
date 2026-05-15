from django.db.models import Count
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from api.filters import EncomiendaFilter
from api.pagination import CustomPagination
from api.permissions import IsAdminOrReadOnly
from api.throttling import SustainedRateThrottle
from envios.models import Encomienda
from envios.serializers import EncomiendaListSerializer, EncomiendaV2Serializer


class EncomiendaViewSetV2(viewsets.ModelViewSet):
    """
    API v2: viewset extendido para encomiendas.
    """

    queryset = Encomienda.objects.con_relaciones().order_by("codigo")
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = EncomiendaFilter
    search_fields = ["codigo", "descripcion", "remitente__apellidos", "destinatario__apellidos"]
    ordering_fields = ["codigo", "fecha_registro", "peso_kg", "costo_envio"]
    throttle_classes = [SustainedRateThrottle]
    permission_classes = [IsAdminOrReadOnly]
    pagination_class = CustomPagination

    def get_serializer_class(self):
        if self.action == "list":
            return EncomiendaListSerializer
        return EncomiendaV2Serializer

    @action(detail=False, methods=["get"])
    def stats(self, request):
        total_encomiendas = Encomienda.objects.count()
        con_retraso = Encomienda.objects.con_retraso().count()
        distribucion_por_estado = (
            Encomienda.objects.values("estado")
            .annotate(encomiendas_count=Count("id"))
            .order_by("estado")
        )
        return Response(
            {
                "total_encomiendas": total_encomiendas,
                "con_retraso": con_retraso,
                "distribucion_por_estado": list(distribucion_por_estado),
            }
        )
