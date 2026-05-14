from django.contrib.messages.views import SuccessMessageMixin
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from .forms import EncomiendaForm
from .models import Encomienda
from .views import _empleado_para_usuario


class EncomiendaListView(LoginRequiredMixin, ListView):
    model = Encomienda
    template_name = "envios/lista.html"
    context_object_name = "encomiendas"
    paginate_by = 15

    def get_queryset(self):
        return Encomienda.objects.con_relaciones()


class EncomiendaDetailView(LoginRequiredMixin, DetailView):
    model = Encomienda
    template_name = "envios/detalle.html"
    context_object_name = "encomienda"

    def get_queryset(self):
        return Encomienda.objects.con_relaciones().prefetch_related("historial")


class EncomiendaCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = Encomienda
    form_class = EncomiendaForm
    template_name = "envios/formulario.html"
    success_message = "Encomienda registrada correctamente."

    def form_valid(self, form):
        form.instance.empleado_registro = _empleado_para_usuario(self.request.user)
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("encomienda_detalle", kwargs={"pk": self.object.pk})


class EncomiendaUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Encomienda
    form_class = EncomiendaForm
    template_name = "envios/formulario.html"
    success_message = "Encomienda actualizada correctamente."
    success_url = reverse_lazy("encomienda_lista")
