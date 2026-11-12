from django.contrib import admin

from .models import CierreCaja, MovimientoCaja


class SoloLectura(admin.ModelAdmin):
    """Movimientos y cierres se registran por la API, que aplica las reglas de caja."""

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(MovimientoCaja)
class MovimientoCajaAdmin(SoloLectura):
    list_display = ("id_movimiento", "fecha_movimiento", "tipo_movimiento", "monto", "usuario")
    list_filter = ("tipo_movimiento", "fecha_movimiento")
    search_fields = ("concepto",)


@admin.register(CierreCaja)
class CierreCajaAdmin(SoloLectura):
    list_display = (
        "id_cierre",
        "fecha_hora_cierre",
        "saldo_esperado",
        "efectivo_contado",
        "diferencia",
        "usuario",
    )
    list_filter = ("fecha_hora_cierre",)
