from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class EstadoPedido(models.TextChoices):
    PENDIENTE = "pendiente", "Pendiente"
    EN_PROCESO = "en_proceso", "En proceso"
    FINALIZADO = "finalizado", "Finalizado"


# Listas de E034, E035 y E036. Son valores de ejemplo: quedan a confirmar con ALUMAT.
class TipoVidrio(models.TextChoices):
    SIMPLE_4 = "simple_4", "Simple 4 mm"
    DVH = "dvh_4_9_4", "DVH 4+9+4"
    LAMINADO = "laminado_3_3", "Laminado 3+3"
    TEMPLADO_8 = "templado_8", "Templado 8 mm"


class ColorAluminio(models.TextChoices):
    BLANCO = "blanco", "Blanco"
    NEGRO = "negro", "Negro"
    NATURAL = "natural", "Natural"
    BRONCE = "bronce", "Bronce"


class TipoRevestimiento(models.TextChoices):
    SIMIL_MADERA = "simil_madera", "Símil madera"
    TEXTURADO = "texturado", "Texturado"


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
    # E025: fecha y hora del pedido.
    fecha_pedido = models.DateTimeField("fecha del pedido", default=timezone.now)
    estado = models.CharField(
        max_length=20, choices=Estado.choices, default=Estado.PENDIENTE
    )
    observaciones = models.TextField(blank=True)

    class Meta:
        db_table = "pedidos"
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
    # El producto se obtiene a través del diseño (E030).
    # PROTECT impide borrar diseños usados en detalles de pedido.
    diseno = models.ForeignKey(
        "productos.Diseno",
        on_delete=models.PROTECT,
        db_column="id_diseno",
        related_name="detalles_pedido",
    )
    ancho = models.DecimalField(
        max_digits=6, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))]
    )  # E031, mayor que 0
    alto = models.DecimalField(
        max_digits=6, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))]
    )  # E032, mayor que 0
    cantidad = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])  # E033
    tipo_vidrio = models.CharField(
        "tipo de vidrio", max_length=100, choices=TipoVidrio.choices, blank=True
    )  # E034 condicional
    color_aluminio = models.CharField(
        "color del aluminio", max_length=50, choices=ColorAluminio.choices
    )  # E035 obligatorio
    tipo_revestimiento = models.CharField(
        "tipo de revestimiento", max_length=100, choices=TipoRevestimiento.choices, blank=True
    )  # E036 condicional
    observaciones = models.TextField(blank=True)

    class Meta:
        db_table = "detalle_pedidos"
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
        return f"{self.diseno} x{self.cantidad}"
