from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.db.models import Sum
from django.utils import timezone


class TipoMovimiento(models.TextChoices):
    ENTRADA = "ENTRADA", "Entrada"
    SALIDA = "SALIDA", "Salida"


class MovimientoCaja(models.Model):
    id_movimiento = models.AutoField(primary_key=True)
    # Las columnas conservan el nombre id_*; en Python el campo es el objeto relacionado.
    apertura = models.ForeignKey(
        "cajas.AperturaCaja",
        on_delete=models.PROTECT,
        db_column="id_apertura",
        related_name="movimientos",
    )
    cobro = models.ForeignKey(
        "ventas.Cobro",
        on_delete=models.PROTECT,
        db_column="id_cobro",
        null=True,
        blank=True,
        related_name="movimientos",
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        db_column="id_usuario",
        related_name="movimientos_caja",
    )
    fecha_movimiento = models.DateTimeField(default=timezone.now)
    tipo_movimiento = models.CharField(max_length=10, choices=TipoMovimiento.choices)
    concepto = models.CharField(max_length=255)
    monto = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )

    class Meta:
        db_table = "MOVIMIENTO_CAJAS"
        verbose_name = "Movimiento de Caja"
        verbose_name_plural = "Movimientos de Caja"
        ordering = ["-fecha_movimiento", "-id_movimiento"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(monto__gt=0),
                name="movimiento_monto_positivo",
            ),
            models.CheckConstraint(
                condition=models.Q(tipo_movimiento__in=TipoMovimiento.values),
                name="movimiento_tipo_valido",
            ),
        ]

    def clean(self):
        super().clean()
        errores = {}

        # Solo se registran movimientos nuevos en una apertura abierta.
        if self._state.adding and self.apertura_id is not None:
            from cajas.models import AperturaCaja

            if not AperturaCaja.objects.filter(
                pk=self.apertura_id, estado=AperturaCaja.Estado.ABIERTA
            ).exists():
                errores["apertura"] = "La caja de esta apertura ya está cerrada."

        if self.cobro_id is not None:
            from ventas.models import MetodoPago

            if self.cobro.metodo_pago != MetodoPago.EFECTIVO:
                errores["cobro"] = (
                    "Solo los cobros en efectivo generan movimientos de caja."
                )
            elif self.tipo_movimiento != TipoMovimiento.ENTRADA:
                errores["tipo_movimiento"] = "Un cobro solo puede ser una entrada."

        if errores:
            raise ValidationError(errores)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.tipo_movimiento} - {self.monto} ({self.concepto})"


class CierreCaja(models.Model):
    id_cierre = models.AutoField(primary_key=True)
    apertura = models.ForeignKey(
        "cajas.AperturaCaja",
        on_delete=models.PROTECT,
        db_column="id_apertura",
        related_name="cierres",
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        db_column="id_usuario",
        related_name="cierres_caja",
    )
    fecha_hora_cierre = models.DateTimeField(default=timezone.now)
    total_ingresos = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0")
    )
    total_egresos = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0")
    )
    saldo_esperado = models.DecimalField(max_digits=12, decimal_places=2)
    efectivo_contado = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
    )
    diferencia = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        db_table = "CIERRE_CAJAS"
        verbose_name = "Cierre de Caja"
        verbose_name_plural = "Cierres de Caja"
        ordering = ["-fecha_hora_cierre", "-id_cierre"]
        constraints = [
            # Una apertura se cierra una sola vez.
            models.UniqueConstraint(fields=["apertura"], name="un_cierre_por_apertura"),
            models.CheckConstraint(
                condition=models.Q(efectivo_contado__gte=0),
                name="cierre_efectivo_no_negativo",
            ),
        ]

    def calcular_y_cerrar(self):
        totales = self.apertura.movimientos.aggregate(
            ingresos=Sum("monto", filter=models.Q(tipo_movimiento=TipoMovimiento.ENTRADA)),
            egresos=Sum("monto", filter=models.Q(tipo_movimiento=TipoMovimiento.SALIDA)),
        )
        self.total_ingresos = totales["ingresos"] or Decimal("0")
        self.total_egresos = totales["egresos"] or Decimal("0")
        self.saldo_esperado = (
            self.apertura.monto_inicial + self.total_ingresos - self.total_egresos
        )
        self.diferencia = self.efectivo_contado - self.saldo_esperado

    def save(self, *args, **kwargs):
        if self.pk is not None:
            # Un cierre ya hecho no se recalcula ni cambia de apertura.
            return super().save(*args, **kwargs)

        from cajas.models import AperturaCaja

        with transaction.atomic():
            # Bloquea la apertura para que no entren movimientos mientras se cierra.
            apertura = AperturaCaja.objects.select_for_update().get(pk=self.apertura_id)
            if apertura.estado != AperturaCaja.Estado.ABIERTA:
                raise ValidationError({"apertura": "Esta apertura ya está cerrada."})
            self.apertura = apertura
            self.calcular_y_cerrar()
            super().save(*args, **kwargs)
            apertura.estado = AperturaCaja.Estado.CERRADA
            apertura.save(update_fields=["estado"])

    def __str__(self):
        return f"Cierre #{self.id_cierre} - Apertura #{self.apertura_id}"
