from django.db import models
from django.db.models.functions import Lower
from django.urls import reverse


class Producto(models.Model):
    id_producto = models.BigAutoField(primary_key=True)
    nombre = models.CharField(max_length=120)
    tipo_abertura = models.CharField("tipo de abertura", max_length=80)
    descripcion = models.TextField("descripción", blank=True)
    # Cantidad de aberturas disponibles, sin importar sus medidas. Se descuenta
    # cuando un pedido pasa a producción y se devuelve si se cancela.
    stock = models.PositiveIntegerField(default=0)
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
                violation_error_message=(
                    "Ya existe un producto con ese nombre y tipo de abertura."
                ),
            ),
            models.CheckConstraint(
                condition=models.Q(stock__gte=0), name="producto_stock_no_negativo"
            ),
        ]

    def __str__(self):
        return self.nombre

    def get_absolute_url(self):
        return reverse("productos:detalle", args=[self.pk])


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
                violation_error_message="El producto ya tiene un diseño con ese nombre.",
            ),
        ]

    def __str__(self):
        return self.nombre_diseno
