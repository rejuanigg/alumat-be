from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class EstadoPedido(models.TextChoices):
    PENDIENTE = "pendiente", "Pendiente"
    EN_PRODUCCION = "en_produccion", "En producción"
    TERMINADO = "terminado", "Terminado"
    ENTREGADO = "entregado", "Entregado"
    CANCELADO = "cancelado", "Cancelado"


class Pedido(models.Model):
    Estado = EstadoPedido

    id_pedido = models.BigAutoField(primary_key=True)
    cliente = models.ForeignKey(
        "clientes.Cliente",
        on_delete=models.PROTECT,
        db_column="id_cliente",
        related_name="pedidos",
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        db_column="id_usuario",
        related_name="pedidos",
    )
    fecha_pedido = models.DateField("fecha del pedido", default=timezone.localdate)
    estado = models.CharField(
        max_length=20, choices=Estado.choices, default=Estado.PENDIENTE
    )
    observaciones = models.TextField(blank=True)

    class Meta:
        ordering = ["-fecha_pedido", "-id_pedido"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(estado__in=EstadoPedido.values),
                name="pedido_estado_valido",
            )
        ]

    def __str__(self):
        return f"Pedido {self.id_pedido}"


class DetallePedido(models.Model):
    id_detalle_pedido = models.BigAutoField(primary_key=True)
    pedido = models.ForeignKey(
        Pedido,
        on_delete=models.PROTECT,
        db_column="id_pedido",
        related_name="detalles",
    )
    producto = models.ForeignKey(
        "productos.Producto",
        on_delete=models.PROTECT,
        db_column="id_producto",
        related_name="detalles_pedido",
    )
    # PROTECT impide borrar diseños usados en detalles de pedido.
    diseno = models.ForeignKey(
        "productos.Diseno",
        on_delete=models.PROTECT,
        db_column="id_diseno",
        related_name="detalles_pedido",
    )
    # Medidas en milímetros.
    ancho = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    alto = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    cantidad = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    tipo_vidrio = models.CharField("tipo de vidrio", max_length=80)
    color_aluminio = models.CharField("color del aluminio", max_length=80)
    tipo_revestimiento = models.CharField("tipo de revestimiento", max_length=80)
    observaciones = models.TextField(blank=True)

    class Meta:
        verbose_name = "detalle de pedido"
        verbose_name_plural = "detalles de pedido"
        ordering = ["pedido", "id_detalle_pedido"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(ancho__gt=0)
                & models.Q(alto__gt=0)
                & models.Q(cantidad__gt=0),
                name="detalle_medidas_y_cantidad_positivas",
            )
        ]

    def __str__(self):
        return f"{self.producto} - {self.diseno} x{self.cantidad}"

    def clean(self):
        super().clean()
        self.validar_diseno_del_producto()

    def save(self, *args, **kwargs):
        # También se controla al guardar desde código, no solo desde formularios.
        self.validar_diseno_del_producto()
        super().save(*args, **kwargs)

    def validar_diseno_del_producto(self):
        if self.producto_id is None or self.diseno_id is None:
            return
        from productos.models import Diseno

        if not Diseno.objects.filter(
            pk=self.diseno_id, producto_id=self.producto_id
        ).exists():
            raise ValidationError(
                {"diseno": "El diseño elegido no corresponde al producto."}
            )
