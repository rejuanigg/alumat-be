from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.db import transaction

from productos.models import Diseno, Producto

EJEMPLOS = [
    # (nombre, tipo de abertura, stock, diseños)
    ("Ventana", "Corrediza", 10, ["Dos hojas", "Tres hojas"]),
    ("Puerta", "Batiente", 4, ["Una hoja", "Con paño fijo"]),
    ("Ventiluz", "Banderola", 6, ["Simple"]),
]


class Command(BaseCommand):
    help = (
        "Agrega productos y diseños de ejemplo sin modificar registros existentes. "
        "No crea cuentas."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--usuario", required=True, help="Nombre del administrador existente"
        )

    @transaction.atomic
    def handle(self, *args, **options):
        # Solo un administrador puede cargar ejemplos.
        if not get_user_model().objects.filter(
            username=options["usuario"], is_superuser=True, is_active=True
        ).exists():
            raise CommandError("Primero creá un administrador con createsuperuser.")
        for nombre, tipo, stock, disenos in EJEMPLOS:
            producto = Producto.objects.filter(
                nombre__iexact=nombre, tipo_abertura__iexact=tipo
            ).first()
            if producto is None:
                producto = Producto.objects.create(
                    nombre=nombre, tipo_abertura=tipo, stock=stock
                )
            for nombre_diseno in disenos:
                if not producto.disenos.filter(nombre_diseno__iexact=nombre_diseno).exists():
                    Diseno.objects.create(producto=producto, nombre_diseno=nombre_diseno)
        self.stdout.write(
            self.style.SUCCESS(
                "Ejemplos disponibles; los registros existentes se conservaron."
            )
        )
