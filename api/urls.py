from django.urls import include, path
from rest_framework.routers import DefaultRouter

from envios import api_views
from envios.viewsets import (
    ClienteViewSet,
    EncomiendaViewSet,
    HistorialEstadoViewSet,
    RutaViewSet,
)
from .authentication import EncomiendaTokenView
from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView

router = DefaultRouter()
router.register("encomiendas", EncomiendaViewSet, basename="encomienda")
router.register("clientes", ClienteViewSet, basename="cliente")
router.register("rutas", RutaViewSet, basename="ruta")
router.register("historial", HistorialEstadoViewSet, basename="historial")

urlpatterns = [
    path("", include(router.urls)),
    path("auth/token/", EncomiendaTokenView.as_view(), name="token_obtain"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("auth/token/verify/", TokenVerifyView.as_view(), name="token_verify"),
    path("fbv/encomiendas/", api_views.encomienda_list, name="fbv_encomienda_list"),
    path("fbv/encomiendas/<int:pk>/", api_views.encomienda_detail, name="fbv_encomienda_detail"),
    path("cbv/encomiendas/", api_views.EncomiendaListAPIView.as_view(), name="cbv_encomienda_list"),
    path("cbv/encomiendas/<int:pk>/", api_views.EncomiendaDetailAPIView.as_view(), name="cbv_encomienda_detail"),
    path("mixins/encomiendas/", api_views.EncomiendaListCreateMixinView.as_view(), name="mixins_encomienda_list"),
    path("mixins/encomiendas/<int:pk>/", api_views.EncomiendaRetrieveUpdateDestroyMixinView.as_view(), name="mixins_encomienda_detail"),
    path("generics/encomiendas/", api_views.EncomiendaListCreateView.as_view(), name="generics_encomienda_list"),
    path("generics/encomiendas/<int:pk>/", api_views.EncomiendaDetailView.as_view(), name="generics_encomienda_detail"),
]
