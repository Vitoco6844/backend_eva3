from datetime import timedelta
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from inventory.models import Contractor, Site, Warehouse, Category, Asset
from maintenance.models import MaintenancePlan


class Command(BaseCommand):
    help = "Datos ficticios idempotentes. No crea usuarios ni contraseñas."

    @transaction.atomic
    def handle(self, *args, **kwargs):
        warehouses = []
        for name, address in [
            ("Obra Los Castaños", "Avenida del Proyecto 120, Santiago"),
            ("Edificio Mirador", "Camino de la Obra 450, Santiago"),
            ("Bodega Central", "Calle de la Industria 80, Santiago"),
        ]:
            site, _ = Site.objects.get_or_create(
                name=name, defaults={"address": address}
            )
            warehouse, _ = Warehouse.objects.get_or_create(
                name="Bodega " + name, site=site
            )
            warehouses.append(warehouse)
        for i, name in enumerate(
            ["Constructora Horizonte", "Obras del Valle", "Montajes Cordillera"], 1
        ):
            Contractor.objects.get_or_create(
                tax_id=f"DEMO-{i:03}",
                defaults={
                    "name": name,
                    "email": f"contacto{i}@example.test",
                    "phone": "Datos ficticios",
                },
            )
        rows = [
            ("Taladro percutor", "Perforación", 6000),
            ("Rotomartillo SDS Plus", "Perforación", 9500),
            ("Taladro inalámbrico", "Perforación", 7500),
            ("Esmeril angular 4.5 pulgadas", "Corte y desbaste", 6500),
            ("Sierra circular", "Corte y desbaste", 8500),
            ("Sierra caladora", "Corte y desbaste", 5000),
            ("Compactadora de placa", "Compactación", 28000),
            ("Vibrador de hormigón", "Hormigonado", 18000),
            ("Betonera 160 litros", "Hormigonado", 22000),
            ("Nivel láser", "Medición", 10000),
            ("Generador portátil", "Energía", 25000),
            ("Soldadora inverter", "Soldadura", 16000),
        ]
        for i, (name, category, rate) in enumerate(rows, 1):
            cat, _ = Category.objects.get_or_create(name=category)
            asset, created = Asset.objects.get_or_create(
                code=f"BC-{i:03}",
                defaults={
                    "name": name,
                    "category": cat,
                    "warehouse": warehouses[(i - 1) % 3],
                    "daily_rate": rate,
                    "serial": f"SERIE-DEMO-{i:03}",
                    "description": "Equipo ficticio para demostración académica.",
                },
            )
            if created:
                MaintenancePlan.objects.create(
                    asset=asset,
                    due_at=timezone.now() + timedelta(days=30),
                    due_hours=100,
                )
        self.stdout.write(
            "Catálogo ficticio listo: 12 herramientas, 3 contratistas y 3 bodegas. No se crearon cuentas."
        )
