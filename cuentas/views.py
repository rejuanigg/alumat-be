from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from .forms import RegistroForm, AccesoForm
from .models import Usuario
from .services import resolver_solicitud


class AccesoView(LoginView):
    template_name = "cuentas/login.html"
    authentication_form = AccesoForm
    redirect_authenticated_user = True


def registro(request):
    if request.user.is_authenticated:
        return redirect("inicio:home")
    form = RegistroForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            with transaction.atomic():
                form.save()
        except IntegrityError:
            form.add_error(
                None, "El usuario o correo ya fue registrado. Revisá los datos."
            )
        else:
            return redirect("cuentas:pendiente")
    return render(request, "cuentas/registro.html", {"form": form})


def pendiente(request):
    return render(request, "cuentas/pendiente.html")


@login_required
def solicitudes(request):
    if not request.user.is_superuser:
        raise PermissionDenied
    return render(
        request,
        "cuentas/solicitudes.html",
        {
            "solicitudes": Usuario.objects.filter(estado="pendiente").order_by(
                "date_joined"
            )
        },
    )


@login_required
@require_POST
def resolver(request, pk):
    if not request.user.is_superuser:
        raise PermissionDenied
    get_object_or_404(Usuario, pk=pk)
    accion = request.POST.get("accion")
    if accion not in ("aprobar", "rechazar"):
        raise PermissionDenied
    changed = resolver_solicitud(
        usuario_id=pk, aprobar=accion == "aprobar", administrador=request.user
    )
    messages.success(
        request,
        "Solicitud resuelta." if changed else "La solicitud ya había sido resuelta.",
    )
    return redirect("cuentas:solicitudes")
