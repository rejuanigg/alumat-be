# movimientos_caja/serializers.py
from rest_framework import serializers
from .models import MovimientoCaja, CierreCaja

class MovimientoCajaSerializer(serializers.ModelSerializer):
    class Meta:
        model = MovimientoCaja
        fields = '__all__'
        # Evitamos que pidan el usuario en la petición, ya que lo agregas en la vista
        read_only_fields = ['id_usuario', 'fecha_movimiento'] 

class CierreCajaSerializer(serializers.ModelSerializer):
    class Meta:
        model = CierreCaja
        fields = '__all__'
        read_only_fields = ['id_usuario', 'fecha_hora_cierre', 'total_ingresos', 'total_egresos', 'saldo_esperado', 'diferencia']