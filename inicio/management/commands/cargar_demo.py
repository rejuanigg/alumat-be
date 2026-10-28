from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.db import transaction
from catalogo.models import Categoria, Producto


class Command(BaseCommand):
    help = (
        "Agrega ejemplos ficticios sin modificar registros existentes. No crea cuentas."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--usuario", required=True, help="Nombre del administrador existente"
        )

    @transaction.atomic
    def handle(self, *args, **options):
        try:
            usuario = get_user_model().objects.get(
                username=options["usuario"], is_superuser=True, is_active=True
            )
        except get_user_model().DoesNotExist:
            raise CommandError("Primero creá un administrador con createsuperuser.")
        for codigo, nombre, categoria, precio, stock in [
            ("DEMO-001", "Cuaderno de tapa dura", "Librería", "8500.00", 20),
            ("DEMO-002", "Lápiz de grafito", "Librería", "650.00", 80),
            ("DEMO-003", "Botella reutilizable", "Accesorios", "12000.00", 8),
        ]:
            cat = Categoria.objects.filter(nombre__iexact=categoria).first()
            if not cat:
                cat = Categoria.objects.create(nombre=categoria)
            if not Producto.objects.filter(codigo__iexact=codigo).exists():
                Producto.objects.create(
                    codigo=codigo,
                    nombre=nombre,
                    categoria=cat,
                    precio=precio,
                    stock=stock,
                    creado_por=usuario,
                    actualizado_por=usuario,
                )
        self.stdout.write(
            self.style.SUCCESS(
                "Ejemplos disponibles; los registros existentes se conservaron."
            )
        )
