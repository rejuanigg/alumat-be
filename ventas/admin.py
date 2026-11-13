from django.contrib import admin

from .models import Cobro, Venta


@admin.register(Venta)
class VentaAdmin(admin.ModelAdmin):
    list_display = ("id_venta", "pedido", "usuario", "fecha_venta", "importe_total")
    list_filter = ("fecha_venta",)
    readonly_fields = ("fecha_venta",)

    def has_delete_permission(self, request, obj=None):
        # Las ventas son historial: no se borran.
        return False


@admin.register(Cobro)
class CobroAdmin(admin.ModelAdmin):
    """Solo lectura: el alta se hace con ventas.services.registrar_cobro, que
    controla el saldo y registra la entrada en caja de los cobros en efectivo."""

    list_display = (
        "id_cobro", "venta", "fecha_cobro", "monto", "tipo_cobro", "metodo_pago",
        "numero_boleta", "usuario",
    )
    list_filter = ("tipo_cobro", "metodo_pago", "fecha_cobro")
    search_fields = ("numero_boleta",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
