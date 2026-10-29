from django.db import models


class Producto(models.Model):
    id_producto = models.BigAutoField(primary_key=True)
    nombre = models.CharField(max_length=120)
    tipo_abertura = models.CharField("tipo de abertura", max_length=80)
    descripcion = models.TextField("descripción", blank=True)
    # Se desactiva en lugar de borrar para conservar el historial.
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ["nombre", "id_producto"]

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

    def __str__(self):
        return self.nombre_diseno
