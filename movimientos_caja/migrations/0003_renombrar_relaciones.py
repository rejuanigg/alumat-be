from django.db import migrations, models


def restriccion_unica(nombre, campo):
    return models.UniqueConstraint(fields=(campo,), name=nombre)


class Migration(migrations.Migration):
    """Renombra los campos en Python; las columnas id_* de la base no cambian.

    Las restricciones únicas se actualizan solo en el estado de Django: en la
    base siguen apuntando a las mismas columnas y no hace falta recrearlas.
    """

    dependencies = [
        ("movimientos_caja", "0002_cierrecaja_cierre_efectivo_no_negativo_and_more"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.RemoveConstraint("cierrecaja", "cierre_unico_por_apertura"),
                migrations.RemoveConstraint("movimientocaja", "movimiento_cobro_unico"),
            ],
        ),
        migrations.RenameField("movimientocaja", "id_apertura", "apertura"),
        migrations.RenameField("movimientocaja", "id_cobro", "cobro"),
        migrations.RenameField("movimientocaja", "id_usuario", "usuario"),
        migrations.RenameField("cierrecaja", "id_apertura", "apertura"),
        migrations.RenameField("cierrecaja", "id_usuario", "usuario"),
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddConstraint(
                    "cierrecaja", restriccion_unica("cierre_unico_por_apertura", "apertura")
                ),
                migrations.AddConstraint(
                    "movimientocaja", restriccion_unica("movimiento_cobro_unico", "cobro")
                ),
            ],
        ),
    ]
