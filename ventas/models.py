from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Sum


class Venta(models.Model):
    id_venta = models.BigAutoField(primary_key=True)                       # E048
    pedido = models.OneToOneField("pedidos.Pedido", on_delete=models.PROTECT,
                                  db_column="id_pedido", related_name="venta")   # E049, UNIQUE
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                                db_column="id_usuario", related_name="ventas")  # E050
    fecha_venta = models.DateTimeField(auto_now_add=True)                   # E051
    importe_total = models.DecimalField(max_digits=12, decimal_places=2,
                                        validators=[MinValueValidator(Decimal("0.01"))])  # E052 > 0

    class Meta:
        db_table = "ventas"
        ordering = ["-fecha_venta", "-id_venta"]
        constraints = [models.CheckConstraint(condition=models.Q(importe_total__gt=0), name="venta_importe_positivo")]

    @property
    def total_cobrado(self):
        return self.cobros.aggregate(t=Sum("monto"))["t"] or Decimal("0")

    @property
    def saldo_pendiente(self):
        return self.importe_total - self.total_cobrado

    def __str__(self):
        return f"Venta #{self.id_venta}"


class MetodoPago(models.TextChoices):
    EFECTIVO = "efectivo", "Efectivo"
    TRANSFERENCIA = "transferencia", "Transferencia bancaria"
    TARJETA_DEBITO = "tarjeta_debito", "Tarjeta de débito"
    TARJETA_CREDITO = "tarjeta_credito", "Tarjeta de crédito"


class TipoCobro(models.TextChoices):
    PARCIAL = "parcial", "Parcial"
    TOTAL = "total", "Total"


class Cobro(models.Model):
    MetodoPago = MetodoPago
    TipoCobro = TipoCobro

    id_cobro = models.BigAutoField(primary_key=True)  # E053
    venta = models.ForeignKey(
        Venta,
        on_delete=models.PROTECT,
        related_name="cobros",
        db_column="id_venta",
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        db_column="id_usuario",
        related_name="cobros",
    )  # E055
    fecha_cobro = models.DateTimeField(auto_now_add=True)
    monto = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    tipo_cobro = models.CharField(max_length=20, choices=TipoCobro.choices)  # E058
    metodo_pago = models.CharField(
        "método de pago", max_length=30, choices=MetodoPago.choices
    )  # E059
    numero_boleta = models.CharField(
        max_length=30,
        unique=True,
        error_messages={"unique": "Ese número de boleta ya fue registrado."},
    )  # E060

    class Meta:
        db_table = "cobros"
        ordering = ["-fecha_cobro", "-id_cobro"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(monto__gt=0),
                name="cobro_monto_positivo",
            ),
            models.CheckConstraint(
                condition=models.Q(metodo_pago__in=MetodoPago.values),
                name="cobro_metodo_pago_valido",
            ),
            models.CheckConstraint(
                condition=models.Q(tipo_cobro__in=TipoCobro.values),
                name="cobro_tipo_valido",
            ),
        ]

    def clean(self):
        super().clean()
        if self._state.adding and self.venta_id and self.monto is not None:
            saldo = self.venta.saldo_pendiente
            if self.monto > saldo:
                raise ValidationError({"monto": "El monto no puede superar el saldo pendiente de la venta."})
            if self.tipo_cobro == TipoCobro.TOTAL and self.monto != saldo:
                raise ValidationError({"tipo_cobro": "Un cobro total debe cubrir todo el saldo pendiente."})
            if self.tipo_cobro == TipoCobro.PARCIAL and self.monto == saldo:
                raise ValidationError({"tipo_cobro": "El monto cubre todo el saldo: el cobro es total."})

    def __str__(self):
        return f"Cobro #{self.id_cobro} - Venta #{self.venta_id}"
