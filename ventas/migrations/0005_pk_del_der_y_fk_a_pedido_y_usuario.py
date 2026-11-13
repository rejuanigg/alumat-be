import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def exigir_tablas_vacias(apps, schema_editor):
    """Las FK nuevas son obligatorias y no hay de dónde sacar su valor:
    si ya hay ventas o cobros cargados, se detiene en lugar de inventarlo."""
    for modelo in ("Venta", "Cobro"):
        if apps.get_model("ventas", modelo).objects.exists():
            raise RuntimeError(
                f"Hay filas en {modelo}: hay que decidir a qué pedido y usuario "
                "asignarlas antes de agregar las FK obligatorias."
            )


class Migration(migrations.Migration):

    dependencies = [
        ("ventas", "0004_metodo_pago_opciones"),
        ("pedidos", "0005_detalle_sin_producto_y_listas"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Los PK se renombran (no se borran y recrean): MovimientoCaja.cobro
        # sigue apuntando a la misma columna.
        migrations.RenameField("venta", "id", "id_venta"),
        migrations.RenameField("cobro", "id", "id_cobro"),
        # Solo cambia la definición en Python (sin "ID" automático); no toca la base.
        migrations.AlterField(
            model_name="venta",
            name="id_venta",
            field=models.BigAutoField(primary_key=True, serialize=False),
        ),
        migrations.AlterField(
            model_name="cobro",
            name="id_cobro",
            field=models.BigAutoField(primary_key=True, serialize=False),
        ),
        migrations.RunPython(exigir_tablas_vacias, migrations.RunPython.noop),
        migrations.AddField(
            model_name="venta",
            name="pedido",
            field=models.OneToOneField(
                db_column="id_pedido",
                on_delete=django.db.models.deletion.PROTECT,
                related_name="venta",
                to="pedidos.pedido",
            ),
        ),
        migrations.AddField(
            model_name="venta",
            name="usuario",
            field=models.ForeignKey(
                db_column="id_usuario",
                on_delete=django.db.models.deletion.PROTECT,
                related_name="ventas",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="cobro",
            name="usuario",
            field=models.ForeignKey(
                db_column="id_usuario",
                on_delete=django.db.models.deletion.PROTECT,
                related_name="cobros",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
