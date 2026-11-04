from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone

class TipoMovimiento(models.TextChoices):
    ENTRADA = 'ENTRADA', 'Entrada'
    SALIDA = 'SALIDA', 'Salida'

class MovimientoCaja(models.Model):
    id_movimiento = models.AutoField(primary_key=True)
    id_apertura = models.ForeignKey(
        'cajas.AperturaCaja',
        on_delete=models.PROTECT,
        db_column='id_apertura',
        related_name='movimientos'
    )
    id_cobro = models.ForeignKey(
    'ventas.Cobro',  # O el nombre correcto de la app donde vive Cobro
    on_delete=models.PROTECT,
    db_column='id_cobro',
    null=True,
    blank=True,
    related_name='movimientos'
)
    id_usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        db_column='id_usuario'
    )
    fecha_movimiento = models.DateTimeField(default=timezone.now)
    tipo_movimiento = models.CharField(
        max_length=10,
        choices=TipoMovimiento.choices
    )
    concepto = models.CharField(max_length=255)
    monto = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        db_table = 'MOVIMIENTO_CAJAS'
        verbose_name = 'Movimiento de Caja'
        verbose_name_plural = 'Movimientos de Caja'

    def clean(self):
        super().clean()
        if self.id_cobro:
            medio = getattr(self.id_cobro, 'medio_pago', '').lower()
            if any(pago in medio for pago in ['transferencia', 'tarjeta']):
                raise ValidationError(
                    "Los cobros por transferencia o tarjeta no deben generar movimientos de efectivo."
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.tipo_movimiento} - {self.monto} ({self.concepto})"


class CierreCaja(models.Model):
    id_cierre = models.AutoField(primary_key=True)
    id_apertura = models.ForeignKey(
        'cajas.AperturaCaja',
        on_delete=models.PROTECT,
        db_column='id_apertura',
        related_name='cierres'
    )
    id_usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        db_column='id_usuario'
    )
    fecha_hora_cierre = models.DateTimeField(default=timezone.now)
    total_ingresos = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    total_egresos = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    saldo_esperado = models.DecimalField(max_digits=12, decimal_places=2)
    efectivo_contado = models.DecimalField(max_digits=12, decimal_places=2)
    diferencia = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        db_table = 'CIERRE_CAJAS'
        verbose_name = 'Cierre de Caja'
        verbose_name_plural = 'Cierres de Caja'

    def calcular_y_cerrar(self):
        movimientos = self.id_apertura.movimientos.all()
        ingresos = sum(m.monto for m in movimientos if m.tipo_movimiento == TipoMovimiento.ENTRADA)
        egresos = sum(m.monto for m in movimientos if m.tipo_movimiento == TipoMovimiento.SALIDA)
        monto_inicial = getattr(self.id_apertura, 'monto_inicial', 0.00)

        self.total_ingresos = ingresos
        self.total_egresos = egresos
        self.saldo_esperado = monto_inicial + ingresos - egresos
        self.diferencia = self.efectivo_contado - self.saldo_esperado

    def save(self, *args, **kwargs):
        if not self.pk:
            self.calcular_y_cerrar()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Cierre #{self.id_cierre} - Apertura #{self.id_apertura_id}"

