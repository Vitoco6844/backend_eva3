from datetime import timedelta
from decimal import Decimal
from django.core.exceptions import ValidationError, PermissionDenied
from django.utils import timezone
from tests.base import DomainCase, signature
from inventory.models import Asset
from rentals.services import issue_loan, return_items, refresh_overdue_alerts
from rentals.models import OverdueAlert


class RentalTests(DomainCase):
    def test_issue_and_double_issue(self):
        loan = self.issue()
        self.asset.refresh_from_db()
        self.assertEqual(self.asset.status, "EN_USO")
        self.assertEqual(loan.signatures.count(), 1)
        with self.assertRaises(ValidationError):
            self.issue()

    def test_partial_return_and_repeated_return(self):
        other = Asset.objects.create(
            code="T-002",
            name="Otro",
            category=self.category,
            warehouse=self.warehouse,
            daily_rate=2000,
        )
        loan = self.issue([self.asset.pk, other.pk])
        item = loan.items.get(asset=self.asset)
        return_items(
            loan_id=loan.pk,
            items=[
                {
                    "item_id": item.pk,
                    "usage_hours": "1.25",
                    "damaged": False,
                    "notes": "",
                }
            ],
            signature=signature(),
            actor=self.operator,
        )
        loan.refresh_from_db()
        self.assertIsNone(loan.closed_at)
        self.assertFalse(hasattr(loan, "charge"))
        with self.assertRaises(ValidationError):
            return_items(
                loan_id=loan.pk,
                items=[{"item_id": item.pk, "usage_hours": "1.25"}],
                signature=signature(),
                actor=self.operator,
            )
        self.asset.refresh_from_db()
        self.assertEqual(self.asset.usage_hours, Decimal("1.25"))

    def test_overdue_blocks_without_job(self):
        loan = self.issue()
        loan.issued_at = timezone.now() - timedelta(days=3)
        loan.due_at = timezone.now() - timedelta(days=1)
        loan.save()
        other = Asset.objects.create(
            code="T-002",
            name="Otro",
            category=self.category,
            warehouse=self.warehouse,
            daily_rate=1000,
        )
        with self.assertRaises(ValidationError):
            self.issue([other.pk])
        refresh_overdue_alerts()
        refresh_overdue_alerts()
        self.assertEqual(OverdueAlert.objects.count(), 1)

    def test_invalid_signature_rolls_back(self):
        with self.assertRaises(ValidationError):
            self.issue(signature="data:image/png;base64,AAAA")
        self.assertEqual(self.asset.loan_items.count(), 0)

    def test_customer_cannot_issue(self):
        with self.assertRaises(PermissionDenied):
            self.issue(actor=self.customer)

    def test_invalid_return_hours_rolls_back(self):
        loan = self.issue()
        for hours in ["-1", "NaN", "Infinity", "0.001"]:
            with self.subTest(hours=hours), self.assertRaises(ValidationError):
                return_items(
                    loan_id=loan.pk,
                    items=[{"item_id": loan.items.get().pk, "usage_hours": hours}],
                    signature=signature(),
                    actor=self.operator,
                )
