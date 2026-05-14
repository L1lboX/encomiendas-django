from django.contrib import admin
from django.utils.html import format_html

from .models import Empleado, Encomienda, HistorialEstado


@admin.register(Encomienda)
class EncomiendaAdmin(admin.ModelAdmin):
    list_display = (
        "codigo",
        "remitente",
        "destinatario",
        "ruta",
        "estado_badge",
        "fecha_registro",
    )
    list_filter = ("estado", "ruta")
    search_fields = ("codigo", "remitente__nro_doc", "destinatario__nro_doc")
    readonly_fields = ("fecha_registro",)
    fieldsets = (
        (
            "Identificacion",
            {"fields": ("codigo", "descripcion", "peso_kg", "volumen_cm3")},
        ),
        (
            "Personas y ruta",
            {"fields": ("remitente", "destinatario", "ruta", "empleado_registro")},
        ),
        (
            "Estado y costos",
            {
                "fields": (
                    "estado",
                    "costo_envio",
                    "fecha_registro",
                    "fecha_entrega_est",
                    "fecha_entrega_real",
                    "observaciones",
                )
            },
        ),
    )

    @admin.display(description="Estado", ordering="estado")
    def estado_badge(self, obj):
        colors = {
            "PE": "#7c3aed",
            "TR": "#0369a1",
            "DE": "#b45309",
            "EN": "#15803d",
            "DV": "#b91c1c",
        }
        color = colors.get(obj.estado, "#334155")
        return format_html(
            '<span style="background:{}; color:#fff; padding:3px 8px; border-radius:999px;">{}</span>',
            color,
            obj.get_estado_display(),
        )


@admin.register(Empleado)
class EmpleadoAdmin(admin.ModelAdmin):
    list_display = ("codigo", "apellidos", "nombres", "cargo", "estado")
    search_fields = ("codigo", "apellidos", "nombres")


@admin.register(HistorialEstado)
class HistorialEstadoAdmin(admin.ModelAdmin):
    list_display = (
        "encomienda",
        "estado_anterior",
        "estado_nuevo",
        "empleado",
        "fecha_cambio",
    )
    readonly_fields = ("fecha_cambio",)


admin.site.site_header = "Sistema de Gestion de Encomiendas"
admin.site.site_title = "Encomiendas"
admin.site.index_title = "Administracion del sistema"
