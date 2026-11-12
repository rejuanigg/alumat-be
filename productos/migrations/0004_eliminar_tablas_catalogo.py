from django.db import migrations

# La app "catalogo" (plantilla inicial del proyecto) se reemplazó por
# productos.Producto. Esta migración borra sus tablas en las bases donde
# existan; en una base nueva no hace nada.
BORRAR_TABLAS = """
DROP TABLE IF EXISTS catalogo_producto;
DROP TABLE IF EXISTS catalogo_categoria;
DELETE FROM django_migrations WHERE app = 'catalogo';
"""


def borrar_tipos_de_contenido(apps, schema_editor):
    # Sus permisos y entradas del historial del admin se borran en cascada.
    ContentType = apps.get_model("contenttypes", "ContentType")
    ContentType.objects.filter(app_label="catalogo").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("productos", "0003_stock"),
        ("contenttypes", "0002_remove_content_type_name"),
    ]

    operations = [
        migrations.RunSQL(BORRAR_TABLAS, reverse_sql=migrations.RunSQL.noop),
        migrations.RunPython(borrar_tipos_de_contenido, migrations.RunPython.noop),
    ]
