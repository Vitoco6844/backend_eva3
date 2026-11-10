from datetime import timedelta
from django.test import TransactionTestCase
from django.db import connection, IntegrityError, transaction
from django.db.migrations.executor import MigrationExecutor
from django.utils import timezone


class PrepaidMigrationTests(TransactionTestCase):
    def test_old_documents_survive_and_new_defaults_are_prepaid(self):
        executor = MigrationExecutor(connection)
        latest = executor.loader.graph.leaf_nodes()
        old = [
            ("accounts", "0003_customer_email_identity"),
            ("inventory", "0003_asset_catalog_image"),
            ("rentals", "0002_customer_rental_requests"),
            ("payments", "0001_initial"),
            ("maintenance", "0001_initial"),
        ]
        executor.migrate(old)
        try:
            apps = executor.loader.project_state(old).apps
            user = apps.get_model("accounts", "User").objects.create(
                username="old", password="preserved-hash"
            )
            contractor = apps.get_model("inventory", "Contractor").objects.create(
                name="Old", tax_id="OLD"
            )
            site = apps.get_model("inventory", "Site").objects.create(
                name="Old", address="Old"
            )
            now = timezone.now()
            Loan = apps.get_model("rentals", "Loan")
            loan = Loan.objects.create(
                contractor_id=contractor.pk,
                site_id=site.pk,
                actor_id=user.pk,
                responsible="Old",
                issued_at=now,
                due_at=now + timedelta(days=2),
            )
            charge = apps.get_model("payments", "Charge").objects.create(
                loan_id=loan.pk, amount=12000, paid_at=now
            )
            attempt = apps.get_model("payments", "PaymentAttempt").objects.create(
                charge_id=charge.pk, order="old-order", amount=12000, status="APPROVED"
            )
        finally:
            executor = MigrationExecutor(connection)
            executor.migrate(latest)
        from rentals.models import Loan as CurrentLoan
        from payments.models import Charge, PaymentAttempt
        from accounts.models import User

        self.assertEqual(
            CurrentLoan.objects.get(pk=loan.pk).billing_mode, "LEGACY_POSTPAID"
        )
        self.assertEqual(CurrentLoan._meta.get_field("billing_mode").default, "PREPAID")
        self.assertEqual(Charge.objects.get(pk=charge.pk).kind, "LEGACY")
        self.assertEqual(Charge.objects.get(pk=charge.pk).amount, 12000)
        self.assertIsNotNone(Charge.objects.get(pk=charge.pk).paid_at)
        self.assertEqual(PaymentAttempt.objects.get(pk=attempt.pk).status, "APPROVED")
        self.assertEqual(User.objects.get(pk=user.pk).password, "preserved-hash")
