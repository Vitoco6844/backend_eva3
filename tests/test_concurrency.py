from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import patch
from django.test import TransactionTestCase
from django.db import close_old_connections
from tests.base import DomainCase, signature
from tests import test_prepaid_payments as helpers
from rentals.models import LoanItem
from rentals.services import issue_loan


class ConcurrencyTests(TransactionTestCase):
    setUp = DomainCase.setUp
    request = helpers.PrepaidPayments.request
    approve = helpers.PrepaidPayments.approve
    paid_request = helpers.PrepaidPayments.paid_request

    def test_one_asset_cannot_be_issued_twice_concurrently(self):
        req = self.paid_request()
        barrier = Barrier(2)

        def worker(_):
            close_old_connections()
            try:
                barrier.wait(timeout=15)
                return issue_loan(
                    request_id=req.pk,
                    contractor_id=req.contractor_id,
                    site_id=self.site.pk,
                    asset_ids=[self.asset.pk],
                    due_at=req.ends_at,
                    responsible="Ana",
                    signature=signature(),
                    actor=self.operator,
                ).pk
            finally:
                close_old_connections()

        with (
            patch("rentals.services.timezone.now", return_value=req.starts_at),
            ThreadPoolExecutor(max_workers=2) as pool,
        ):
            results = list(pool.map(worker, [1, 2]))
        self.assertEqual(results[0], results[1])
        self.assertEqual(LoanItem.objects.filter(returned_at=None).count(), 1)
