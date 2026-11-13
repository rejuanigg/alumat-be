import django.utils.timezone
from django.db import migrations, models

# Estados viejos -> estados del documento (E026).
A_NUEVOS = {
    "pendiente": "pendiente",
    "en_produccion": "en_proceso",
    "terminado": "en_proceso",
    "entregado": "finalizado",
}
# La reversa no puede distinguir en_produccion de terminado: vuelve a en_produccion.
A_VIEJOS = {
    "pendiente": "pendiente",
    "en_proceso": "en_produccion",
    "finalizado": "entregado",
}


def convertir(apps, tabla):
    Pedido = apps.get_model("pedidos", "Pedido")
    desconocidos = set(Pedido.objects.values_list("estado", flat=True)) - set(tabla)
    if desconocidos:
        # Por ejemplo "cancelado": el documento no lo contempla.
        raise RuntimeError(
            f"Hay pedidos con estados que no se pueden convertir: {sorted(desconocidos)}"
        )
    for viejo, nuevo in tabla.items():
        if viejo != nuevo:
            Pedido.objects.filter(estado=viejo).update(estado=nuevo)


def estados_nuevos(apps, schema_editor):
    convertir(apps, A_NUEVOS)


def estados_viejos(apps, schema_editor):
    convertir(apps, A_VIEJOS)


class Migration(migrations.Migration):

    dependencies = [
        ("pedidos", "0003_quitar_stock_descontado"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="pedido",
            name="pedido_estado_valido",
        ),
        migrations.AlterField(
            model_name="pedido",
            name="estado",
            field=models.CharField(
                choices=[
                    ("pendiente", "Pendiente"),
                    ("en_proceso", "En proceso"),
                    ("finalizado", "Finalizado"),
                ],
                default="pendiente",
                max_length=20,
            ),
        ),
        migrations.RunPython(estados_nuevos, estados_viejos),
        migrations.AddConstraint(
            model_name="pedido",
            constraint=models.CheckConstraint(
                condition=models.Q(("estado__in", ["pendiente", "en_proceso", "finalizado"])),
                name="pedido_estado_valido",
            ),
        ),
        migrations.AlterField(
            model_name="pedido",
            name="fecha_pedido",
            field=models.DateTimeField(
                default=django.utils.timezone.now, verbose_name="fecha del pedido"
            ),
        ),
        migrations.AlterModelTable(
            name="pedido",
            table="pedidos",
        ),
    ]
