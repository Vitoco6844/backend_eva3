from django.test import TransactionTestCase
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.utils import timezone
from datetime import timedelta


class IdentityMigrationTests(TransactionTestCase):
    old_targets = [
        ("accounts", "0002_initial"),
        ("inventory", "0001_initial"),
        ("rentals", "0001_initial"),
        ("payments", "0001_initial"),
        ("maintenance", "0001_initial"),
    ]

    def setUp(self):
        executor = MigrationExecutor(connection)
        self.latest = executor.loader.graph.leaf_nodes()
        executor.migrate(self.old_targets)
        self.old = executor.loader.project_state(self.old_targets).apps

    def tearDown(self):
        Contractor = self.old.get_model("inventory", "Contractor")
        Contractor.objects.filter(tax_id="12345678-5").delete()
        executor = MigrationExecutor(connection)
        executor.migrate(self.latest)
        super().tearDown()

    def test_existing_account_and_loan_survive(self):
        User = self.old.get_model("accounts", "User")
        Contractor = self.old.get_model("inventory", "Contractor")
        Site = self.old.get_model("inventory", "Site")
        Loan = self.old.get_model("rentals", "Loan")
        contractor = Contractor.objects.create(name="Empresa", tax_id="DEMO-OLD")
        user = User.objects.create(
            username="admin_preservado",
            role="ADMIN",
            password="hash-preservado",
            is_staff=True,
        )
        site = Site.objects.create(name="Obra", address="Dirección")
        now = timezone.now()
        loan = Loan.objects.create(
            contractor=contractor,
            site=site,
            responsible="Ana",
            actor=user,
            issued_at=now,
            due_at=now + timedelta(days=1),
        )
        executor = MigrationExecutor(connection)
        executor.migrate(self.latest)
        from accounts.models import User as CurrentUser
        from rentals.models import Loan as CurrentLoan

        self.assertEqual(
            CurrentUser.objects.get(pk=user.pk).password, "hash-preservado"
        )
        self.assertEqual(
            CurrentLoan.objects.get(pk=loan.pk).contractor_id, contractor.pk
        )

    def test_normalized_collision_aborts_without_deleting_records(self):
        Contractor = self.old.get_model("inventory", "Contractor")
        Contractor.objects.create(name="Primera", tax_id="12.345.678-5")
        Contractor.objects.create(name="Segunda", tax_id="12345678-5")
        executor = MigrationExecutor(connection)
        with self.assertRaisesMessage(RuntimeError, "identificaciones"):
            executor.migrate(self.latest)
        self.assertEqual(Contractor.objects.count(), 2)
