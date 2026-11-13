from django.contrib import admin

from .models import Cliente


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ("id_cliente", "__str__", "tipo_cliente", "dni", "cuit", "telefono", "activo")
    list_filter = ("tipo_cliente", "activo")
    search_fields = ("nombre", "apellido", "razon_social", "dni", "cuit")
    readonly_fields = ("fecha_registro",)

    def has_delete_permission(self, request, obj=None):
        # No se borran clientes: se desactivan (baja lógica).
        return False
