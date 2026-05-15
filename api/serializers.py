from rest_framework import serializers

from envios.models import Encomienda
from envios.serializers import EncomiendaSerializer


class DynamicFieldsModelSerializer(serializers.ModelSerializer):
    """
    ModelSerializer que acepta un argumento `fields` para limitar la salida.
    """

    def __init__(self, *args, **kwargs):
        fields = kwargs.pop("fields", None)
        super().__init__(*args, **kwargs)

        if fields is not None:
            allowed = set(fields)
            existing = set(self.fields)
            for field_name in existing - allowed:
                self.fields.pop(field_name)


class EncomiendaDynamicSerializer(DynamicFieldsModelSerializer):
    ruta_codigo = serializers.CharField(source="ruta.codigo", read_only=True)
    ruta_destino = serializers.CharField(source="ruta.destino", read_only=True)
    remitente_nombre = serializers.CharField(source="remitente.nombre_completo", read_only=True)
    destinatario_nombre = serializers.CharField(source="destinatario.nombre_completo", read_only=True)

    class Meta:
        model = Encomienda
        fields = [
            "id",
            "codigo",
            "descripcion",
            "estado",
            "ruta_codigo",
            "ruta_destino",
            "remitente_nombre",
            "destinatario_nombre",
            "peso_kg",
            "costo_envio",
        ]


__all__ = [
    "DynamicFieldsModelSerializer",
    "EncomiendaDynamicSerializer",
    "EncomiendaSerializer",
]
