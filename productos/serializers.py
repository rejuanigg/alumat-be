from rest_framework import serializers
from .models import Diseno, Producto


class ProductoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Producto
        fields = ("id_producto", "nombre", "tipo_abertura", "descripcion", "activo")


class DisenoSerializer(serializers.ModelSerializer):
    id_producto = serializers.PrimaryKeyRelatedField(
        source="producto",
        queryset=Producto.objects.all(),
        error_messages={"does_not_exist": "El producto indicado no existe."},
    )

    class Meta:
        model = Diseno
        fields = ("id_diseno", "id_producto", "nombre_diseno", "activo")

    def validate_id_producto(self, producto):
        # La asociación diseño-producto no cambia después de crearse.
        if self.instance is not None and producto != self.instance.producto:
            raise serializers.ValidationError(
                "El producto de un diseño no se puede modificar."
            )
        return producto
