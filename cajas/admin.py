from django.contrib import admin

from .models import AperturaCaja, Caja


@admin.register(Caja)
class CajaAdmin(admin.ModelAdmin):
    list_display = ("id_caja", "nombre_caja", "activa")
    list_filter = ("activa",)
    search_fields = ("nombre_caja",)

    def has_delete_permission(self, request, obj=None):
        # Una caja se desactiva en lugar de borrarse, para conservar su historial.
        return False


@admin.register(AperturaCaja)
class AperturaCajaAdmin(admin.ModelAdmin):
    """Solo lectura: las aperturas se registran por la API y se cierran con el cierre de caja."""

    list_display = ("id_apertura", "caja", "usuario", "fecha_hora_apertura", "monto_inicial", "estado")
    list_filter = ("estado", "caja")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
