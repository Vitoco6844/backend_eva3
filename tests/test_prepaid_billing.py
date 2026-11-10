from datetime import timedelta
from unittest.mock import patch
from django.utils import timezone
from tests.base import DomainCase, signature
from tests import test_prepaid_payments as helpers
from rentals.services import return_items
from payments.models import Charge


class PrepaidBilling(DomainCase):
    request = helpers.PrepaidPayments.request
    approve = helpers.PrepaidPayments.approve
    paid_request = helpers.PrepaidPayments.paid_request
    deliver = helpers.PrepaidPayments.deliver

    def test_on_time_and_early_return_do_not_create_extra(self):
        from payments.services import close_charge

        req = self.paid_request()
        loan = self.deliver(req)
        with patch(
            "rentals.services.timezone.now",
            return_value=req.ends_at - timedelta(hours=2),
        ):
            return_items(
                loan_id=loan.pk,
                items=[{"item_id": loan.items.get().pk, "usage_hours": 1}],
                signature=signature(),
                actor=self.operator,
            )
        loan.refresh_from_db()
        self.assertIsNone(close_charge(loan))
        self.assertEqual(
            list(loan.charges.values_list("kind", "amount")), [("INITIAL", 12000)]
        )

    def test_ten_hours_late_creates_only_one_extra_day(self):
        from payments.services import close_charge

        req = self.paid_request()
        loan = self.deliver(req)
        with patch(
            "rentals.services.timezone.now",
            return_value=req.ends_at + timedelta(hours=10),
        ):
            return_items(
                loan_id=loan.pk,
                items=[{"item_id": loan.items.get().pk, "usage_hours": 1}],
                signature=signature(),
                actor=self.operator,
            )
        loan.refresh_from_db()
        extra = close_charge(loan)
        self.assertEqual(extra.amount, 6000)
        self.assertEqual(extra.kind, "EXTRA")
        self.assertEqual(close_charge(loan).pk, extra.pk)
        self.assertEqual(Charge.objects.filter(loan=loan).count(), 2)

    def test_partial_return_bills_late_lines_only(self):
        from rentals.models import RentalRequestItem, AssetHold
        from inventory.models import Asset

        req = self.paid_request()
        # Fixture de contrato con dos líneas; la prueba de aprobación cubre su creación.
        other = Asset.objects.create(
            code="OTHER",
            name="Otro",
            category=self.category,
            warehouse=self.warehouse,
            daily_rate=3000,
        )
        RentalRequestItem.objects.create(
            request=req,
            asset=other,
            estimated_daily_rate=3000,
            approved_daily_rate=3000,
        )
        AssetHold.objects.create(request=req, asset=other)
        req.approved_amount = 18000
        req.save()
        req.charges.update(amount=18000)
        loan = self.deliver(req)
        with patch("rentals.services.timezone.now", return_value=req.ends_at):
            return_items(
                loan_id=loan.pk,
                items=[
                    {"item_id": loan.items.get(asset=self.asset).pk, "usage_hours": 1}
                ],
                signature=signature(),
                actor=self.operator,
            )
        self.assertFalse(loan.charges.filter(kind="EXTRA").exists())
        with patch(
            "rentals.services.timezone.now",
            return_value=req.ends_at + timedelta(hours=10),
        ):
            return_items(
                loan_id=loan.pk,
                items=[{"item_id": loan.items.get(asset=other).pk, "usage_hours": 1}],
                signature=signature(),
                actor=self.operator,
            )
        self.assertEqual(loan.charges.get(kind="EXTRA").amount, 3000)

    def test_extra_units_count_real_time_across_dst(self):
        from payments.billing import units
        from datetime import datetime
        from zoneinfo import ZoneInfo

        zone = ZoneInfo("America/Santiago")
        self.assertEqual(
            units(
                datetime(2026, 4, 4, 12, tzinfo=zone),
                datetime(2026, 4, 5, 12, tzinfo=zone),
            ),
            2,
        )
        self.assertEqual(
            units(
                datetime(2026, 4, 5, 12, tzinfo=zone),
                datetime(2026, 4, 4, 12, tzinfo=zone),
            ),
            0,
        )
