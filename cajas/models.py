from decimal import Decimal
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class Caja(models.Model):
    id_caja = models.BigAutoField(primary_key=True)
    nombre_caja = models.CharField("nombre de la caja", max_length=80)
    # Se desactiva en lugar de borrar para conservar el historial.
    activa = models.BooleanField(default=True)

    class Meta:
        ordering = ["nombre_caja", "id_caja"]

    def __str__(self):
        return self.nombre_caja


class EstadoApertura(models.TextChoices):
    ABIERTA = "abierta", "Abierta"
    CERRADA = "cerrada", "Cerrada"


class AperturaCaja(models.Model):
    Estado = EstadoApertura

    id_apertura = models.BigAutoField(primary_key=True)
    # PROTECT impide borrar una caja que tenga aperturas.
    caja = models.ForeignKey(
        "cajas.Caja",
        on_delete=models.PROTECT,
        db_column="id_caja",
        related_name="aperturas",
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        db_column="id_usuario",
        related_name="aperturas_caja",
    )
    fecha_hora_apertura = models.DateTimeField(
        "fecha y hora de apertura", default=timezone.now
    )
    monto_inicial = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0"))]
    )
    estado = models.CharField(
        max_length=10, choices=EstadoApertura.choices, default=EstadoApertura.ABIERTA
    )
    # Los movimientos y el cierre deben referenciar AperturaCaja con
    # on_delete=models.PROTECT para impedir borrar aperturas con registros.

    class Meta:
        verbose_name = "apertura de caja"
        verbose_name_plural = "aperturas de caja"
        ordering = ["-fecha_hora_apertura", "-id_apertura"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(estado__in=EstadoApertura.values),
                name="apertura_estado_valido",
            ),
            models.CheckConstraint(
                condition=models.Q(monto_inicial__gte=0),
                name="apertura_monto_inicial_no_negativo",
            ),
            # Una caja no puede tener dos aperturas abiertas a la vez.
            models.UniqueConstraint(
                fields=["caja"],
                condition=models.Q(estado="abierta"),
                name="una_apertura_abierta_por_caja",
            ),
        ]

    def __str__(self):
        return f"{self.caja} - {self.fecha_hora_apertura:%d/%m/%Y %H:%M}"

    def clean(self):
        super().clean()
        self.validar_condiciones()

    def save(self, *args, **kwargs):
        # También se controla al guardar desde código, no solo desde formularios.
        self.validar_condiciones()
        super().save(*args, **kwargs)

    def validar_condiciones(self):
        anterior = (
            AperturaCaja.objects.filter(pk=self.pk).values_list("estado", flat=True).first()
            if self.pk
            else None
        )
        if anterior == self.Estado.CERRADA and self.estado == self.Estado.ABIERTA:
            raise ValidationError({"estado": "Una apertura cerrada no se puede reabrir."})
        if self.estado != self.Estado.ABIERTA or self.caja_id is None:
            return
        if anterior is None and not Caja.objects.filter(
            pk=self.caja_id, activa=True
        ).exists():
            raise ValidationError({"caja": "No se puede abrir una caja inactiva."})
        if (
            AperturaCaja.objects.filter(caja_id=self.caja_id, estado=self.Estado.ABIERTA)
            .exclude(pk=self.pk)
            .exists()
        ):
            raise ValidationError({"caja": "La caja ya tiene una apertura abierta."})
