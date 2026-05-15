from decimal import Decimal

from rest_framework import serializers

from clientes.models import Cliente
from config.choices import EstadoEnvio
from rutas.models import Ruta
from .models import Empleado, Encomienda, HistorialEstado


class ClienteSerializer(serializers.ModelSerializer):
    nombre_completo = serializers.ReadOnlyField()
    esta_activo = serializers.ReadOnlyField()

    class Meta:
        model = Cliente
        fields = [
            "id",
            "tipo_doc",
            "nro_doc",
            "nombres",
            "apellidos",
            "nombre_completo",
            "telefono",
            "email",
            "esta_activo",
        ]


class RutaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ruta
        fields = [
            "id",
            "codigo",
            "origen",
            "destino",
            "precio_base",
            "dias_entrega",
            "estado",
        ]


class HistorialEstadoSerializer(serializers.ModelSerializer):
    empleado_nombre = serializers.StringRelatedField(source="empleado")
    estado_anterior_display = serializers.CharField(
        source="get_estado_anterior_display",
        read_only=True,
    )
    estado_nuevo_display = serializers.CharField(
        source="get_estado_nuevo_display",
        read_only=True,
    )

    class Meta:
        model = HistorialEstado
        fields = [
            "id",
            "estado_anterior",
            "estado_anterior_display",
            "estado_nuevo",
            "estado_nuevo_display",
            "empleado_nombre",
            "observacion",
            "fecha_cambio",
        ]


class EncomiendaBulkSerializer(serializers.ListSerializer):
    def create(self, validated_data):
        encomiendas = [Encomienda(**item) for item in validated_data]
        return Encomienda.objects.bulk_create(encomiendas)

    def update(self, instances, validated_data):
        instance_map = {enc.id: enc for enc in instances}
        updated = []

        for item in validated_data:
            enc_id = item.pop("id", None)
            enc = instance_map.get(enc_id)
            if enc:
                for campo, valor in item.items():
                    setattr(enc, campo, valor)
                updated.append(enc)

        if updated:
            Encomienda.objects.bulk_update(
                updated,
                ["estado", "observaciones", "costo_envio"],
            )
        return updated


class EncomiendaSerializer(serializers.ModelSerializer):
    esta_entregada = serializers.ReadOnlyField()
    tiene_retraso = serializers.ReadOnlyField()
    dias_en_transito = serializers.ReadOnlyField()
    descripcion_corta = serializers.ReadOnlyField()
    estado_display = serializers.SerializerMethodField()
    remitente_id = serializers.PrimaryKeyRelatedField(
        queryset=Cliente.objects.activos(),
        write_only=True,
        source="remitente",
    )
    destinatario_id = serializers.PrimaryKeyRelatedField(
        queryset=Cliente.objects.activos(),
        write_only=True,
        source="destinatario",
    )
    ruta_id = serializers.PrimaryKeyRelatedField(
        queryset=Ruta.objects.activas(),
        write_only=True,
        source="ruta",
    )

    class Meta:
        model = Encomienda
        fields = [
            "id",
            "codigo",
            "descripcion",
            "descripcion_corta",
            "peso_kg",
            "volumen_cm3",
            "costo_envio",
            "remitente",
            "destinatario",
            "ruta",
            "remitente_id",
            "destinatario_id",
            "ruta_id",
            "empleado_registro",
            "estado",
            "estado_display",
            "fecha_registro",
            "fecha_entrega_est",
            "fecha_entrega_real",
            "esta_entregada",
            "tiene_retraso",
            "dias_en_transito",
            "observaciones",
        ]
        read_only_fields = [
            "remitente",
            "destinatario",
            "ruta",
            "empleado_registro",
            "fecha_registro",
            "fecha_entrega_real",
        ]
        list_serializer_class = EncomiendaBulkSerializer

    def get_estado_display(self, obj):
        return obj.get_estado_display()

    def validate_peso_kg(self, value):
        if value <= 0:
            raise serializers.ValidationError("El peso debe ser mayor que cero.")
        return value

    def validate_codigo(self, value):
        value = value.strip().upper()
        if not value.startswith("ENC-"):
            raise serializers.ValidationError("El codigo debe iniciar con ENC-.")
        return value

    def validate(self, data):
        remitente = data.get("remitente", getattr(self.instance, "remitente", None))
        destinatario = data.get(
            "destinatario",
            getattr(self.instance, "destinatario", None),
        )
        if remitente and destinatario and remitente == destinatario:
            raise serializers.ValidationError(
                {"destinatario_id": "El destinatario no puede ser el mismo que el remitente."}
            )
        return data

    def to_internal_value(self, data):
        data = data.copy()
        if data.get("codigo"):
            data["codigo"] = data["codigo"].strip().upper()
        if data.get("descripcion"):
            data["descripcion"] = data["descripcion"].strip()
        if data.get("costo_envio") not in (None, ""):
            data["costo_envio"] = str(Decimal(str(data["costo_envio"])).quantize(Decimal("0.01")))
        return super().to_internal_value(data)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["ruta_codigo"] = instance.ruta.codigo
        data["ruta_origen"] = instance.ruta.origen
        data["ruta_destino"] = instance.ruta.destino
        data["costo_display"] = f"S/ {instance.costo_envio:.2f}"
        data["estado_color"] = {
            EstadoEnvio.PENDIENTE: "gray",
            EstadoEnvio.EN_TRANSITO: "blue",
            EstadoEnvio.EN_DESTINO: "orange",
            EstadoEnvio.ENTREGADO: "green",
            EstadoEnvio.DEVUELTO: "red",
        }.get(instance.estado, "gray")

        request = self.context.get("request")
        if request and not request.user.is_staff:
            data.pop("observaciones", None)
            data.pop("empleado_registro", None)
        return data


class EncomiendaListSerializer(serializers.ModelSerializer):
    remitente_nombre = serializers.ReadOnlyField(source="remitente.nombre_completo")
    destinatario_nombre = serializers.ReadOnlyField(source="destinatario.nombre_completo")
    ruta_destino = serializers.ReadOnlyField(source="ruta.destino")
    estado_display = serializers.SerializerMethodField()
    tiene_retraso = serializers.ReadOnlyField()

    class Meta:
        model = Encomienda
        fields = [
            "id",
            "codigo",
            "estado",
            "estado_display",
            "remitente_nombre",
            "destinatario_nombre",
            "ruta_destino",
            "peso_kg",
            "costo_envio",
            "fecha_registro",
            "fecha_entrega_est",
            "tiene_retraso",
        ]

    def get_estado_display(self, obj):
        return obj.get_estado_display()


class EncomiendaDetailSerializer(EncomiendaSerializer):
    remitente = ClienteSerializer(read_only=True)
    destinatario = ClienteSerializer(read_only=True)
    ruta = RutaSerializer(read_only=True)
    historial = HistorialEstadoSerializer(many=True, read_only=True)

    class Meta(EncomiendaSerializer.Meta):
        fields = EncomiendaSerializer.Meta.fields + ["historial"]


class EncomiendaV2Serializer(EncomiendaDetailSerializer):
    empleado_nombre = serializers.StringRelatedField(source="empleado_registro")

    class Meta(EncomiendaDetailSerializer.Meta):
        fields = EncomiendaDetailSerializer.Meta.fields + ["empleado_nombre"]
