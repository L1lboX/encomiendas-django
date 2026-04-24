import uuid
from datetime import timedelta
from decimal import Decimal

from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from clientes.models import Cliente
from config.choices import EstadoEnvio, EstadoGeneral
from rutas.models import Ruta
from .querysets import EncomiendaQuerySet
from .validators import validar_codigo_encomienda, validar_peso_positivo


class Empleado(models.Model):
    codigo = models.CharField(max_length=10, unique=True)
    nombres = models.CharField(max_length=100)
    apellidos = models.CharField(max_length=100)
    cargo = models.CharField(max_length=80)
    email = models.EmailField(unique=True)
    telefono = models.CharField(max_length=15, blank=True, null=True)
    estado = models.IntegerField(
        choices=EstadoGeneral.choices,
        default=EstadoGeneral.ACTIVO,
    )
    fecha_ingreso = models.DateField()
    rutas_asignadas = models.ManyToManyField(
        "rutas.Ruta",
        blank=True,
        related_name="empleados_asignados",
    )

    def __str__(self):
        return f"{self.codigo} - {self.apellidos}, {self.nombres}"

    class Meta:
        db_table = "empleados"
        verbose_name = "Empleado"
        verbose_name_plural = "Empleados"
        ordering = ["apellidos"]


class PerfilEmpleado(models.Model):
    empleado = models.OneToOneField(
        Empleado,
        on_delete=models.CASCADE,
        related_name="perfil",
    )
    foto = models.ImageField(upload_to="empleados/", null=True, blank=True)
    bio = models.TextField(blank=True)
    linkedin = models.URLField(blank=True)

    def __str__(self):
        return f"Perfil de {self.empleado}"


class Encomienda(models.Model):
    objects = EncomiendaQuerySet.as_manager()

    # Identificacion
    codigo = models.CharField(
        max_length=20,
        unique=True,
        validators=[validar_codigo_encomienda],
    )
    descripcion = models.TextField()
    peso_kg = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[
            validar_peso_positivo,
            MinValueValidator(0.01, message="El peso minimo es 0.01 kg"),
        ],
    )
    volumen_cm3 = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )

    # Relaciones
    remitente = models.ForeignKey(
        Cliente,
        on_delete=models.PROTECT,
        related_name="envios_como_remitente",
    )
    destinatario = models.ForeignKey(
        Cliente,
        on_delete=models.PROTECT,
        related_name="envios_como_destinatario",
    )
    ruta = models.ForeignKey(
        Ruta,
        on_delete=models.PROTECT,
        related_name="encomiendas",
    )
    empleado_registro = models.ForeignKey(
        Empleado,
        on_delete=models.PROTECT,
        related_name="encomiendas_registradas",
    )

    # Estado y fechas
    estado = models.CharField(
        max_length=2,
        choices=EstadoEnvio.choices,
        default=EstadoEnvio.PENDIENTE,
    )
    costo_envio = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    fecha_registro = models.DateTimeField(auto_now_add=True)
    fecha_entrega_est = models.DateField(null=True, blank=True)
    fecha_entrega_real = models.DateField(null=True, blank=True)
    observaciones = models.TextField(blank=True, null=True)

    def clean(self):
        """Validaciones cruzadas entre campos del modelo."""
        super().clean()
        errors = {}

        if self.remitente_id and self.destinatario_id:
            if self.remitente_id == self.destinatario_id:
                errors["destinatario"] = ValidationError(
                    "El destinatario no puede ser el mismo que el remitente."
                )

        if self.fecha_entrega_est:
            if self.fecha_entrega_est < timezone.now().date():
                errors["fecha_entrega_est"] = ValidationError(
                    "La fecha de entrega estimada no puede ser en el pasado."
                )

        if self.fecha_entrega_est and self.fecha_entrega_real:
            if self.fecha_entrega_real < self.fecha_entrega_est:
                errors["fecha_entrega_real"] = ValidationError(
                    "La fecha de entrega real no puede ser antes de la estimada."
                )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        """Ejecuta full_clean() antes de guardar."""
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def esta_entregada(self):
        return self.estado == EstadoEnvio.ENTREGADO

    @property
    def esta_en_transito(self):
        return self.estado == EstadoEnvio.EN_TRANSITO

    @property
    def dias_en_transito(self):
        """Dias transcurridos desde el registro."""
        if not self.fecha_registro:
            return 0
        delta = timezone.now().date() - self.fecha_registro.date()
        return delta.days

    @property
    def tiene_retraso(self):
        """True si la fecha estimada ya paso y no esta entregada."""
        if not self.fecha_entrega_est or self.esta_entregada:
            return False
        return timezone.now().date() > self.fecha_entrega_est

    @property
    def descripcion_corta(self):
        """Primeros 50 caracteres de la descripcion."""
        if len(self.descripcion) > 50:
            return f"{self.descripcion[:50]}..."
        return self.descripcion

    def cambiar_estado(self, nuevo_estado, empleado, observacion=""):
        """
        Cambia el estado de la encomienda y registra el cambio automaticamente.
        """
        if nuevo_estado == self.estado:
            raise ValueError(
                "La encomienda ya se encuentra en estado "
                f"{self.get_estado_display()}"
            )

        estado_anterior = self.estado
        self.estado = nuevo_estado

        if nuevo_estado == EstadoEnvio.ENTREGADO:
            fecha_actual = timezone.now().date()
            if self.fecha_entrega_est and fecha_actual < self.fecha_entrega_est:
                self.fecha_entrega_real = self.fecha_entrega_est
            else:
                self.fecha_entrega_real = fecha_actual

        self.save()

        HistorialEstado.objects.create(
            encomienda=self,
            estado_anterior=estado_anterior,
            estado_nuevo=nuevo_estado,
            empleado=empleado,
            observacion=observacion,
        )
        return self

    def calcular_costo(self):
        """
        Calcula el costo del envio basandose en la ruta y el peso del paquete.
        """
        precio_por_kg_extra = Decimal("2.50")
        peso_base = Decimal("5.0")
        costo = self.ruta.precio_base

        if self.peso_kg > peso_base:
            costo += (self.peso_kg - peso_base) * precio_por_kg_extra

        return round(costo, 2)

    @classmethod
    def crear_con_costo_calculado(
        cls,
        remitente,
        destinatario,
        ruta,
        empleado,
        descripcion,
        peso_kg,
        **kwargs,
    ):
        """
        Crea una encomienda calculando el costo automaticamente.
        """
        codigo = (
            f"ENC-{timezone.now().strftime('%Y%m%d')}-"
            f"{str(uuid.uuid4())[:6].upper()}"
        )
        fecha_est = timezone.now().date() + timedelta(days=ruta.dias_entrega)

        encomienda = cls(
            codigo=codigo,
            descripcion=descripcion,
            peso_kg=peso_kg,
            remitente=remitente,
            destinatario=destinatario,
            ruta=ruta,
            empleado_registro=empleado,
            fecha_entrega_est=fecha_est,
            **kwargs,
        )
        encomienda.costo_envio = encomienda.calcular_costo()
        encomienda.save()
        return encomienda

    def __str__(self):
        return f"{self.codigo} [{self.get_estado_display()}]"

    class Meta:
        db_table = "encomiendas"
        verbose_name = "Encomienda"
        verbose_name_plural = "Encomiendas"
        ordering = ["-fecha_registro"]


class HistorialEstado(models.Model):
    encomienda = models.ForeignKey(
        Encomienda,
        on_delete=models.CASCADE,
        related_name="historial",
    )
    estado_anterior = models.CharField(max_length=2, choices=EstadoEnvio.choices)
    estado_nuevo = models.CharField(max_length=2, choices=EstadoEnvio.choices)
    observacion = models.TextField(blank=True, null=True)
    empleado = models.ForeignKey(
        Empleado,
        on_delete=models.PROTECT,
        related_name="cambios_estado",
    )
    fecha_cambio = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return (
            f"{self.encomienda.codigo}: "
            f"{self.estado_anterior}->{self.estado_nuevo}"
        )

    class Meta:
        db_table = "historial_estados"
        ordering = ["-fecha_cambio"]
