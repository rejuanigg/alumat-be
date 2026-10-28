from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models.functions import Lower
from django.urls import reverse


class Categoria(models.Model):
    nombre = models.CharField(max_length=80, unique=True)

    class Meta:
        ordering = ["nombre"]
        verbose_name = "categoría"
        constraints = [
            models.UniqueConstraint(
                Lower("nombre"), name="categoria_nombre_sin_mayusculas"
            )
        ]

    def __str__(self):
        return self.nombre


class Producto(models.Model):
    codigo = models.CharField("código", max_length=30, unique=True)
    nombre = models.CharField(max_length=120)
    categoria = models.ForeignKey(
        Categoria, on_delete=models.PROTECT, verbose_name="categoría"
    )
    descripcion = models.TextField("descripción", blank=True, max_length=2000)
    precio = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(0)]
    )
    stock = models.PositiveIntegerField(default=0)
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="productos_creados",
    )
    actualizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="productos_actualizados",
    )
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["nombre", "pk"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(precio__gte=0), name="producto_precio_no_negativo"
            ),
            models.UniqueConstraint(
                Lower("codigo"), name="producto_codigo_sin_mayusculas"
            ),
        ]

    def __str__(self):
        return self.nombre

    def get_absolute_url(self):
        return reverse("catalogo:detalle", args=[self.pk])
