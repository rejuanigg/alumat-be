from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    """Renombra los campos en Python; las columnas id_* de la base no cambian."""

    dependencies = [
        ("movimientos_caja", "0002_cierre_unico_y_montos"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RemoveConstraint("cierrecaja", "un_cierre_por_apertura"),
        migrations.RenameField("movimientocaja", "id_apertura", "apertura"),
        migrations.RenameField("movimientocaja", "id_cobro", "cobro"),
        migrations.RenameField("movimientocaja", "id_usuario", "usuario"),
        migrations.RenameField("cierrecaja", "id_apertura", "apertura"),
        migrations.RenameField("cierrecaja", "id_usuario", "usuario"),
        migrations.AlterField(
            model_name="movimientocaja",
            name="usuario",
            field=models.ForeignKey(
                db_column="id_usuario",
                on_delete=models.PROTECT,
                related_name="movimientos_caja",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="cierrecaja",
            name="usuario",
            field=models.ForeignKey(
                db_column="id_usuario",
                on_delete=models.PROTECT,
                related_name="cierres_caja",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddConstraint(
            model_name="cierrecaja",
            constraint=models.UniqueConstraint(
                fields=("apertura",), name="un_cierre_por_apertura"
            ),
        ),
    ]
