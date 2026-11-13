from django.db import migrations, models

A_MINUSCULAS = {"ENTRADA": "entrada", "SALIDA": "salida"}


def convertir(apps, tabla):
    MovimientoCaja = apps.get_model("movimientos_caja", "MovimientoCaja")
    desconocidos = (
        set(MovimientoCaja.objects.values_list("tipo_movimiento", flat=True)) - set(tabla)
    )
    if desconocidos:
        raise RuntimeError(
            f"Hay movimientos con tipos que no se pueden convertir: {sorted(desconocidos)}"
        )
    for viejo, nuevo in tabla.items():
        MovimientoCaja.objects.filter(tipo_movimiento=viejo).update(tipo_movimiento=nuevo)


def a_minusculas(apps, schema_editor):
    convertir(apps, A_MINUSCULAS)


def a_mayusculas(apps, schema_editor):
    convertir(apps, {nuevo: viejo for viejo, nuevo in A_MINUSCULAS.items()})


class Migration(migrations.Migration):

    dependencies = [
        ("movimientos_caja", "0004_validaciones_y_orden"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="movimientocaja",
            name="movimiento_tipo_valido",
        ),
        migrations.AlterField(
            model_name="movimientocaja",
            name="tipo_movimiento",
            field=models.CharField(
                choices=[("entrada", "Entrada"), ("salida", "Salida")], max_length=10
            ),
        ),
        migrations.RunPython(a_minusculas, a_mayusculas),
        migrations.AddConstraint(
            model_name="movimientocaja",
            constraint=models.CheckConstraint(
                condition=models.Q(("tipo_movimiento__in", ["entrada", "salida"])),
                name="movimiento_tipo_valido",
            ),
        ),
        migrations.AlterField(
            model_name="movimientocaja",
            name="concepto",
            field=models.CharField(max_length=200),
        ),
        migrations.AlterModelTable(
            name="movimientocaja",
            table="movimiento_cajas",
        ),
        migrations.AlterModelTable(
            name="cierrecaja",
            table="cierre_cajas",
        ),
    ]
