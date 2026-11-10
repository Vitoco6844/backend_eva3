from django.core.management.base import BaseCommand
from rentals.services import refresh_overdue_alerts
from inventory.models import Asset
from maintenance.services import is_due


class Command(BaseCommand):
    help = "Revisar morosidad y mantenimiento; operación idempotente."

    def handle(self, *args, **options):
        created = refresh_overdue_alerts()
        due = sum(is_due(a) for a in Asset.objects.exclude(status="BAJA"))
        self.stdout.write(
            f"Alertas nuevas: {created}. Activos con revisión vencida: {due}."
        )
