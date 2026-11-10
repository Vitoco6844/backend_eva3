from django.contrib import admin
from django.apps import apps
from django.test import RequestFactory
from tests.base import DomainCase
from accounts.models import User


class AdminTests(DomainCase):
    def test_all_domain_models_registered(self):
        for label in ["accounts", "inventory", "rentals", "maintenance", "payments"]:
            for model in apps.get_app_config(label).get_models():
                with self.subTest(model=model.__name__):
                    self.assertIn(model, admin.site._registry)

    def test_transactional_records_are_readonly(self):
        from rentals.models import Loan, Signature
        from inventory.models import AssetEvent
        from payments.models import PaymentAttempt, Charge
        from maintenance.models import MaintenanceJob

        request = RequestFactory().get("/admin/")
        request.user = User.objects.create_superuser(
            "admin", password="ClaveSegura.123"
        )
        for model in [
            Loan,
            Signature,
            AssetEvent,
            PaymentAttempt,
            Charge,
            MaintenanceJob,
        ]:
            with self.subTest(model=model.__name__):
                panel = admin.site._registry.get(model)
                self.assertIsNotNone(panel)
                if panel:
                    self.assertFalse(panel.has_add_permission(request))
                    self.assertFalse(panel.has_delete_permission(request))
