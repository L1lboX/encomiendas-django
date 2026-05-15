from rest_framework import permissions
from rest_framework.permissions import BasePermission

from config.choices import EstadoGeneral
from envios.models import Empleado


class EsEmpleadoActivo(BasePermission):
    message = "Solo empleados activos tienen acceso a esta API."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return Empleado.objects.filter(
            email=request.user.email,
            estado=EstadoGeneral.ACTIVO,
        ).exists()


class EsPropietarioOAdmin(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.user.is_staff:
            return True
        return obj.empleado_registro.email == request.user.email


class IsAdminOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.is_staff


class IsOwnerOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        owner = getattr(obj, "creado_por", None)
        if owner is not None:
            return owner == request.user
        empleado = getattr(obj, "empleado_registro", None)
        return empleado is not None and empleado.email == request.user.email
