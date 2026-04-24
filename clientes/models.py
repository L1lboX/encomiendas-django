from django.core.exceptions import ValidationError
from django.db import models

from config.choices import EstadoGeneral, TipoDocumento
from envios.querysets import ClienteQuerySet
from envios.validators import validar_nro_doc_dni


class Cliente(models.Model):
    objects = ClienteQuerySet.as_manager()

    tipo_doc = models.CharField(
        max_length=3,
        choices=TipoDocumento.choices,
        default=TipoDocumento.DNI,
    )
    nro_doc = models.CharField(max_length=15, unique=True)
    nombres = models.CharField(max_length=100)
    apellidos = models.CharField(max_length=100)
    telefono = models.CharField(max_length=15, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    direccion = models.TextField(blank=True, null=True)
    estado = models.IntegerField(
        choices=EstadoGeneral.choices,
        default=EstadoGeneral.ACTIVO,
    )
    fecha_registro = models.DateTimeField(auto_now_add=True)

    def clean(self):
        super().clean()
        if self.tipo_doc == TipoDocumento.DNI:
            try:
                validar_nro_doc_dni(self.nro_doc)
            except ValidationError as exc:
                raise ValidationError({"nro_doc": exc.messages})

    @property
    def nombre_completo(self):
        """Nombre y apellidos en formato legible."""
        return f"{self.apellidos}, {self.nombres}"

    @property
    def esta_activo(self):
        """Devuelve True si el estado es ACTIVO."""
        return self.estado == EstadoGeneral.ACTIVO

    @property
    def total_encomiendas_enviadas(self):
        """Numero de encomiendas donde este cliente es remitente."""
        return self.envios_como_remitente.count()

    def __str__(self):
        return f"{self.nro_doc} - {self.apellidos}, {self.nombres}"

    class Meta:
        db_table = "clientes"
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"
        ordering = ["apellidos", "nombres"]
