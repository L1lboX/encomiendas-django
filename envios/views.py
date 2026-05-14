from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import models
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from config.choices import EstadoEnvio, EstadoGeneral
from .forms import CambiarEstadoForm, EncomiendaForm
from .models import Empleado, Encomienda


def _empleado_para_usuario(user):
    empleado = None
    if user.email:
        empleado = Empleado.objects.filter(email__iexact=user.email).first()
    if empleado is None:
        empleado = Empleado.objects.filter(
            models.Q(email__iexact=user.username) | models.Q(codigo__iexact=user.username)
        ).first()
    if empleado is None:
        empleado = Empleado.objects.filter(estado=EstadoGeneral.ACTIVO).first()
    return empleado


@login_required
def dashboard(request):
    encomiendas = Encomienda.objects.con_relaciones()
    ultimas = encomiendas[:8]
    total_activas = encomiendas.activas().count()
    total_transito = encomiendas.en_transito().count()
    total_retraso = encomiendas.con_retraso().count()
    total_entregadas = encomiendas.entregadas().count()
    context = {
        "total_activas": total_activas,
        "total_transito": total_transito,
        "total_retraso": total_retraso,
        "total_entregadas": total_entregadas,
        "stats": [
            ("Activas", total_activas, "primary", "shipping-fast"),
            ("En transito", total_transito, "info", "truck"),
            ("Con retraso", total_retraso, "danger", "exclamation-triangle"),
            ("Entregadas", total_entregadas, "success", "check-circle"),
        ],
        "ultimas_encomiendas": ultimas,
    }
    return render(request, "envios/dashboard.html", context)


@login_required
def encomienda_lista(request):
    estado = request.GET.get("estado", "").strip()
    q = request.GET.get("q", "").strip()
    encomiendas = Encomienda.objects.con_relaciones()

    if estado:
        encomiendas = encomiendas.filter(estado=estado)

    if q:
        encomiendas = encomiendas.filter(
            models.Q(codigo__icontains=q)
            | models.Q(descripcion__icontains=q)
            | models.Q(remitente__nro_doc__icontains=q)
            | models.Q(remitente__nombres__icontains=q)
            | models.Q(remitente__apellidos__icontains=q)
            | models.Q(destinatario__nro_doc__icontains=q)
            | models.Q(destinatario__nombres__icontains=q)
            | models.Q(destinatario__apellidos__icontains=q)
            | models.Q(ruta__origen__icontains=q)
            | models.Q(ruta__destino__icontains=q)
        )

    paginator = Paginator(encomiendas, 15)
    page_obj = paginator.get_page(request.GET.get("page"))

    params = request.GET.copy()
    params.pop("page", None)

    context = {
        "page_obj": page_obj,
        "estado_actual": estado,
        "q": q,
        "querystring": params.urlencode(),
    }
    return render(request, "envios/lista.html", context)


@login_required
def encomienda_detalle(request, pk):
    encomienda = get_object_or_404(
        Encomienda.objects.con_relaciones().prefetch_related("historial"),
        pk=pk,
    )
    form_estado = CambiarEstadoForm(initial={"estado": encomienda.estado})
    return render(
        request,
        "envios/detalle.html",
        {"encomienda": encomienda, "form_estado": form_estado},
    )


@login_required
def encomienda_crear(request):
    if request.method == "POST":
        form = EncomiendaForm(request.POST)
        if form.is_valid():
            empleado = _empleado_para_usuario(request.user)
            if empleado is None:
                messages.error(
                    request,
                    "No hay un empleado activo disponible para registrar la encomienda.",
                )
            else:
                encomienda = form.save(commit=False)
                encomienda.empleado_registro = empleado
                encomienda.save()
                messages.success(
                    request,
                    f"Encomienda {encomienda.codigo} registrada correctamente.",
                )
                return redirect("encomienda_detalle", pk=encomienda.pk)
        else:
            messages.error(request, "Revisa los campos marcados antes de continuar.")
    else:
        form = EncomiendaForm()

    return render(request, "envios/formulario.html", {"form": form, "titulo": "Nueva encomienda"})


@login_required
@require_POST
def encomienda_cambiar_estado(request, pk):
    encomienda = get_object_or_404(Encomienda.objects.con_relaciones(), pk=pk)
    form = CambiarEstadoForm(request.POST)

    if form.is_valid():
        empleado = _empleado_para_usuario(request.user)
        if empleado is None:
            messages.error(
                request,
                "No hay un empleado activo disponible para registrar el cambio.",
            )
        else:
            try:
                encomienda.cambiar_estado(
                    form.cleaned_data["estado"],
                    empleado,
                    form.cleaned_data["observacion"],
                )
            except ValueError as exc:
                messages.warning(request, str(exc))
            else:
                messages.success(request, "Estado actualizado correctamente.")
    else:
        messages.error(request, "No se pudo actualizar el estado.")

    return redirect("encomienda_detalle", pk=encomienda.pk)


@login_required
def buscar_por_codigo(request, codigo):
    encomienda = get_object_or_404(Encomienda, codigo__iexact=codigo)
    return redirect("encomienda_detalle", pk=encomienda.pk)
