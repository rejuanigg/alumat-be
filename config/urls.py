from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("cuentas/", include("cuentas.urls")),
    path("productos/", include("productos.urls_web")),
    path("api/", include("clientes.urls")),
    path("api/", include("productos.urls")),
    path("api/", include("pedidos.urls")),
    path("api/", include("cajas.urls")),
    path("", include("inicio.urls")),
    path('api/', include('movimientos_caja.urls')),
]
admin.site.site_header = "Administración de la organización"
admin.site.site_title = "Administración"
