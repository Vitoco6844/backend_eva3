from datetime import timedelta
from unittest.mock import patch
from django.utils import timezone
from tests.base import DomainCase, signature
from rentals.services import return_items


class ChargeTests(DomainCase):
    def test_historical_rate_and_day_rounding(self):
        for seconds, expected in [(3600, 1000), (86400, 1000), (86401, 2000)]:
            with self.subTest(seconds=seconds):
                self.asset.daily_rate = 1000
                self.asset.save(update_fields=["daily_rate"])
                loan = self.issue()
                self.asset.daily_rate = 9000
                self.asset.save(update_fields=["daily_rate"])
                at = loan.issued_at + timedelta(seconds=seconds)
                with patch("rentals.services.timezone.now", return_value=at):
                    return_items(
                        loan_id=loan.pk,
                        items=[{"item_id": loan.items.get().pk, "usage_hours": 1}],
                        signature=signature(),
                        actor=self.operator,
                    )
                self.assertEqual(loan.charge.amount, expected)
