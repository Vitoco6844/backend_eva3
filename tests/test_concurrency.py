from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from datetime import timedelta
from django.test import TransactionTestCase
from django.db import close_old_connections
from django.utils import timezone
from django.core.exceptions import ValidationError
from tests.base import DomainCase, signature
from inventory.models import Contractor
from accounts.models import User
from rentals.models import LoanItem
from rentals.services import issue_loan


class ConcurrencyTests(TransactionTestCase):
    setUp = DomainCase.setUp

    def test_one_asset_cannot_be_issued_twice_concurrently(self):
        second = Contractor.objects.create(name="Otra constructora", tax_id="DEMO-2")
        barrier = Barrier(2)

        def worker(contractor_id):
            close_old_connections()
            try:
                actor = User.objects.get(pk=self.operator.pk)
                barrier.wait(timeout=10)
                try:
                    issue_loan(
                        contractor_id=contractor_id,
                        site_id=self.site.pk,
                        asset_ids=[self.asset.pk],
                        due_at=timezone.now() + timedelta(days=2),
                        responsible="Responsable",
                        signature=signature(),
                        actor=actor,
                    )
                    return "ok"
                except ValidationError:
                    return "blocked"
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(worker, [self.contractor.pk, second.pk]))
        self.assertCountEqual(results, ["ok", "blocked"])
        self.assertEqual(LoanItem.objects.filter(returned_at=None).count(), 1)
