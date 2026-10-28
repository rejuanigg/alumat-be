from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("cuentas/", include("cuentas.urls")),
    path("catalogo/", include("catalogo.urls")),
    path("", include("inicio.urls")),
]
admin.site.site_header = "Administración de la organización"
admin.site.site_title = "Administración"
