from django.contrib import admin
from .models import MovimientoCaja, CierreCaja

@admin.register(MovimientoCaja)
class MovimientoCajaAdmin(admin.ModelAdmin):
    list_display = ('id_movimiento', 'fecha_movimiento', 'tipo_movimiento', 'monto', 'usuario')
    list_filter = ('tipo_movimiento', 'fecha_movimiento')
    search_fields = ('concepto',)

@admin.register(CierreCaja)
class CierreCajaAdmin(admin.ModelAdmin):
    list_display = ('id_cierre', 'fecha_hora_cierre', 'saldo_esperado', 'efectivo_contado', 'diferencia', 'usuario')
    list_filter = ('fecha_hora_cierre',)
