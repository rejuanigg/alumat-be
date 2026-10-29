from django.db import models

# Create your models here.
class Venta(models.Model):
    fecha_venta = models.DateTimeField(auto_now_add=True)
    importe_total = models.DecimalField(max_digits=10, decimal_places=2)
    def __str__(self):
        return f"Venta #{self.id_venta}"
    
class Cobro(models.Model):
    venta = models.ForeignKey(
        Venta,
        on_delete=models.PROTECT,
        related_name="cobros",
        db_column="id_venta",
    )
    fecha_cobro = models.DateTimeField(auto_now_add=True)
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    tipo_cobro = models.CharField(max_length=20)
    metodo_pago = models.CharField(max_length=30)
    numero_boleta = models.CharField(max_length=30, unique=True)
    
    
    def __str__(self):
        return f"Cobro #{self.pk} - Venta #{self.venta_id}"