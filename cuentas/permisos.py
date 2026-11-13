from rest_framework.permissions import SAFE_METHODS, BasePermission

GRUPO_VENDEDOR = "Vendedor"
GRUPO_DUENO = "Dueño"


def es_dueno(user):
    return user.groups.filter(name=GRUPO_DUENO).exists() and not user.is_superuser


class PermisoPorRol(BasePermission):
    """Administrador (superusuario) y Vendedor operan; el Dueño solo consulta."""
    message = "El Dueño solo puede consultar información."

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.method in SAFE_METHODS:
            return True
        return not es_dueno(request.user)
