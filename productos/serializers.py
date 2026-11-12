from rest_framework import serializers
from .models import Diseno, Producto


class ProductoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Producto
        fields = ("id_producto", "nombre", "tipo_abertura", "descripcion", "stock", "activo")

    def validate(self, attrs):
        # Se compara sin mayúsculas: "Ventana" y "VENTANA" son el mismo producto.
        nombre = attrs.get("nombre", getattr(self.instance, "nombre", ""))
        tipo = attrs.get("tipo_abertura", getattr(self.instance, "tipo_abertura", ""))
        repetidos = Producto.objects.filter(
            nombre__iexact=nombre, tipo_abertura__iexact=tipo
        )
        if self.instance is not None:
            repetidos = repetidos.exclude(pk=self.instance.pk)
        if repetidos.exists():
            raise serializers.ValidationError(
                {"nombre": "Ya existe un producto con ese nombre y tipo de abertura."}
            )
        return attrs


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
        if self.instance is None and not producto.activo:
            raise serializers.ValidationError(
                "No se puede agregar un diseño a un producto inactivo."
            )
        return producto

    def validate(self, attrs):
        producto = attrs.get("producto", getattr(self.instance, "producto", None))
        nombre = attrs.get("nombre_diseno", getattr(self.instance, "nombre_diseno", ""))
        repetidos = Diseno.objects.filter(
            producto=producto, nombre_diseno__iexact=nombre
        )
        if self.instance is not None:
            repetidos = repetidos.exclude(pk=self.instance.pk)
        if repetidos.exists():
            raise serializers.ValidationError(
                {"nombre_diseno": "El producto ya tiene un diseño con ese nombre."}
            )
        return attrs
