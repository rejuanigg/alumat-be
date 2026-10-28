"""La decisión de acceso se registra junto con quien la tomó."""

from django.contrib.admin.models import LogEntry, CHANGE
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from .models import Usuario


@transaction.atomic
def resolver_solicitud(*, usuario_id, aprobar, administrador):
    if not administrador.is_active or not administrador.is_superuser:
        raise PermissionError("Solo el administrador puede resolver solicitudes.")
    usuario = Usuario.objects.select_for_update().get(pk=usuario_id)
    if usuario.estado != Usuario.Estado.PENDIENTE:
        return False
    usuario.estado = Usuario.Estado.APROBADO if aprobar else Usuario.Estado.RECHAZADO
    usuario.is_active = aprobar
    usuario.save(update_fields=["estado", "is_active"])
    LogEntry.objects.log_actions(
        user_id=administrador.pk,
        queryset=Usuario.objects.filter(pk=usuario.pk),
        action_flag=CHANGE,
        change_message="Solicitud aprobada" if aprobar else "Solicitud rechazada",
    )
    return True
