from django.db import models
from django.db.models.functions import Lower


class Producto(models.Model):
    id_producto = models.BigAutoField(primary_key=True)
    nombre = models.CharField(max_length=120)
    tipo_abertura = models.CharField("tipo de abertura", max_length=80)
    descripcion = models.TextField("descripción", blank=True)
    # Se desactiva en lugar de borrar para conservar el historial.
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ["nombre", "id_producto"]
        constraints = [
            # Un mismo nombre no se repite dentro del mismo tipo de abertura,
            # sin importar mayúsculas.
            models.UniqueConstraint(
                Lower("nombre"),
                Lower("tipo_abertura"),
                name="producto_nombre_tipo_unico",
            ),
        ]

    def __str__(self):
        return self.nombre


class Diseno(models.Model):
    id_diseno = models.BigAutoField(primary_key=True)
    # PROTECT impide borrar un producto que tenga diseños asociados.
    producto = models.ForeignKey(
        "productos.Producto",
        on_delete=models.PROTECT,
        db_column="id_producto",
        related_name="disenos",
    )
    nombre_diseno = models.CharField("nombre del diseño", max_length=120)
    # Se desactiva en lugar de borrar para conservar el historial.
    # El detalle de pedido debe referenciar Diseno con on_delete=models.PROTECT
    # para impedir borrar diseños usados en pedidos.
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "diseño"
        ordering = ["nombre_diseno", "id_diseno"]
        constraints = [
            # Un producto no puede tener dos diseños con el mismo nombre.
            models.UniqueConstraint(
                "producto",
                Lower("nombre_diseno"),
                name="diseno_nombre_unico_por_producto",
            ),
        ]

    def __str__(self):
        return self.nombre_diseno
