from datetime import timedelta
from django.core.exceptions import ValidationError
from django.utils import timezone
from tests.base import DomainCase
from maintenance.models import MaintenancePlan
from maintenance.services import start_maintenance, finish_maintenance


class MaintenanceTests(DomainCase):
    def test_due_date_blocks_issue(self):
        MaintenancePlan.objects.create(
            asset=self.asset, due_at=timezone.now() - timedelta(seconds=1)
        )
        with self.assertRaises(ValidationError):
            self.issue()

    def test_due_hours_blocks_issue(self):
        MaintenancePlan.objects.create(asset=self.asset, due_hours=0)
        with self.assertRaises(ValidationError):
            self.issue()

    def test_finish_sets_next_limits(self):
        job = start_maintenance(
            asset_id=self.asset.pk, actor=self.operator, notes="Revisión"
        )
        finish_maintenance(
            job_id=job.pk,
            actor=self.operator,
            notes="Revisión completada",
            next_due_at=timezone.now() + timedelta(days=30),
            next_due_hours=100,
        )
        self.asset.refresh_from_db()
        self.assertEqual(self.asset.status, "DISPONIBLE")
        self.assertEqual(self.asset.maintenance_plan.due_hours, 100)
        with self.assertRaises(ValidationError):
            finish_maintenance(
                job_id=job.pk,
                actor=self.operator,
                notes="Repetido",
                next_due_at=None,
                next_due_hours=100,
            )

    def test_in_use_cannot_start(self):
        self.issue()
        with self.assertRaises(ValidationError):
            start_maintenance(asset_id=self.asset.pk, actor=self.operator, notes="No")

    def test_plan_requires_limit(self):
        from maintenance.services import save_plan

        with self.assertRaises(ValidationError):
            save_plan(
                asset_id=self.asset.pk, due_at=None, due_hours=None, actor=self.operator
            )

    def test_job_cannot_open_twice(self):
        start_maintenance(asset_id=self.asset.pk, actor=self.operator, notes="Revisión")
        with self.assertRaises(ValidationError):
            start_maintenance(asset_id=self.asset.pk, actor=self.operator, notes="Otra")

    def test_in_use_due_is_flagged(self):
        self.issue()
        MaintenancePlan.objects.create(asset=self.asset, due_hours=0)
        self.client.force_login(self.operator)
        response = self.client.get("/maintenance/")
        self.assertContains(response, "Revisiones vencidas")
        self.asset.refresh_from_db()
        self.assertEqual(self.asset.status, "EN_USO")

    def test_unknown_asset_is_not_a_server_error(self):
        self.client.force_login(self.operator)
        self.client.raise_request_exception = False
        response = self.client.post(
            "/api/maintenance-jobs/", {"asset_id": 999999, "notes": "No existe"}
        )
        self.assertEqual(response.status_code, 404)
