from django.urls import path

from . import views, views_async

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("health/", views.health_check, name="health"),
    path("dashboard/stats/", views_async.dashboard_stats_async, name="dashboard_stats_async"),
    path("encomiendas/", views.encomienda_lista, name="encomienda_lista"),
    path("encomiendas/nueva/", views.encomienda_crear, name="encomienda_crear"),
    path("encomiendas/<int:pk>/", views.encomienda_detalle, name="encomienda_detalle"),
    path(
        "encomiendas/<int:pk>/estado/",
        views.encomienda_cambiar_estado,
        name="encomienda_cambiar_estado",
    ),
    path(
        "encomiendas/buscar/<str:codigo>/",
        views.buscar_por_codigo,
        name="buscar_por_codigo",
    ),
]
