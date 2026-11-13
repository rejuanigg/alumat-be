from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand

from cuentas.permisos import GRUPO_DUENO, GRUPO_VENDEDOR


class Command(BaseCommand):
    help = (
        "Crea los grupos de los roles del documento (Vendedor y Dueño). "
        "El Administrador es el superusuario. Se puede ejecutar varias veces."
    )

    def handle(self, *args, **options):
        for nombre in (GRUPO_VENDEDOR, GRUPO_DUENO):
            _, creado = Group.objects.get_or_create(name=nombre)
            self.stdout.write(f"{nombre}: {'creado' if creado else 'ya existía'}")
        self.stdout.write(self.style.SUCCESS("Roles disponibles."))
