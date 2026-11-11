from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models


class Venta(models.Model):
    fecha_venta = models.DateTimeField(auto_now_add=True)
    importe_total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
    )

    class Meta:
        ordering = ["-fecha_venta", "-pk"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(importe_total__gte=0),
                name="venta_importe_no_negativo",
            ),
        ]

    def __str__(self):
        return f"Venta #{self.pk}"


class Cobro(models.Model):
    venta = models.ForeignKey(
        Venta,
        on_delete=models.PROTECT,
        related_name="cobros",
        db_column="id_venta",
    )
    fecha_cobro = models.DateTimeField(auto_now_add=True)
    monto = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    tipo_cobro = models.CharField(max_length=20)
    metodo_pago = models.CharField(max_length=30)
    numero_boleta = models.CharField(max_length=30, unique=True)

    class Meta:
        ordering = ["-fecha_cobro", "-pk"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(monto__gt=0),
                name="cobro_monto_positivo",
            ),
        ]

    def __str__(self):
        return f"Cobro #{self.pk} - Venta #{self.venta_id}"
