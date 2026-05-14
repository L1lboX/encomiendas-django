from django import forms
from django.utils import timezone

from clientes.models import Cliente
from config.choices import EstadoEnvio
from rutas.models import Ruta
from .models import Encomienda


class EncomiendaForm(forms.ModelForm):
    class Meta:
        model = Encomienda
        fields = [
            "codigo",
            "descripcion",
            "peso_kg",
            "volumen_cm3",
            "remitente",
            "destinatario",
            "ruta",
            "costo_envio",
            "fecha_entrega_est",
            "observaciones",
        ]
        widgets = {
            "codigo": forms.TextInput(attrs={"class": "form-control"}),
            "descripcion": forms.Textarea(
                attrs={"class": "form-control", "rows": 3}
            ),
            "peso_kg": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01", "min": "0.01"}
            ),
            "volumen_cm3": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01", "min": "0"}
            ),
            "remitente": forms.Select(attrs={"class": "form-select"}),
            "destinatario": forms.Select(attrs={"class": "form-select"}),
            "ruta": forms.Select(attrs={"class": "form-select"}),
            "costo_envio": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01", "min": "0"}
            ),
            "fecha_entrega_est": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "observaciones": forms.Textarea(
                attrs={"class": "form-control", "rows": 2}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["remitente"].queryset = Cliente.objects.activos()
        self.fields["destinatario"].queryset = Cliente.objects.activos()
        self.fields["ruta"].queryset = Ruta.objects.activas()

    def clean(self):
        cleaned_data = super().clean()
        remitente = cleaned_data.get("remitente")
        destinatario = cleaned_data.get("destinatario")

        if remitente and destinatario and remitente == destinatario:
            self.add_error(
                "destinatario",
                "El destinatario no puede ser el mismo que el remitente.",
            )

        fecha_entrega_est = cleaned_data.get("fecha_entrega_est")
        if fecha_entrega_est and fecha_entrega_est < timezone.now().date():
            self.add_error(
                "fecha_entrega_est",
                "La fecha de entrega estimada no puede ser en el pasado.",
            )

        return cleaned_data


class CambiarEstadoForm(forms.Form):
    estado = forms.ChoiceField(
        choices=EstadoEnvio.choices,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    observacion = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 2}),
    )
