from django.contrib.auth.decorators import login_required
from django.db import connection
from django.http import JsonResponse
from django.shortcuts import render
from productos.models import Diseno, Producto
from cuentas.models import Usuario


@login_required
def home(request):
    return render(
        request,
        "inicio/home.html",
        {
            "productos": Producto.objects.filter(activo=True).count(),
            "disenos": Diseno.objects.filter(activo=True, producto__activo=True).count(),
            "pendientes": (
                Usuario.objects.filter(estado="pendiente").count()
                if request.user.is_superuser
                else None
            ),
        },
    )


def salud(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except Exception:
        return JsonResponse({"estado": "no disponible"}, status=503)
    return JsonResponse({"estado": "ok"})
