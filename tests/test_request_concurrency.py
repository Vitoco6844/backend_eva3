import uuid
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from datetime import timedelta
from django.test import TransactionTestCase
from django.db import close_old_connections
from django.utils import timezone
from django.core.exceptions import ValidationError
from tests.base import DomainCase, signature
from accounts.models import User
from inventory.models import Contractor


class RequestConcurrencyTests(TransactionTestCase):
    setUp = DomainCase.setUp

    def request_for(self, user):
        from rentals.request_services import submit_request

        now = timezone.now() + timedelta(days=1)
        return submit_request(
            actor=user,
            asset_ids=[self.asset.pk],
            site_name="Obra",
            site_address="Dirección",
            responsible="Ana",
            starts_at=now,
            ends_at=now + timedelta(days=1),
            notes="",
            submit_key=uuid.uuid4(),
        )

    def race(self, actions):
        barrier = Barrier(2)

        def worker(args):
            close_old_connections()
            try:
                kind, pk, user_id = args
                actor = User.objects.get(pk=user_id)
                barrier.wait(timeout=10)
                from rentals.request_services import cancel_request, fulfill_request

                try:
                    if kind == "cancel":
                        cancel_request(request_id=pk, actor=actor)
                    else:
                        fulfill_request(
                            request_id=pk,
                            site_id=self.site.pk,
                            responsible="Ana",
                            due_at=timezone.now() + timedelta(days=3),
                            signature=signature(),
                            actor=actor,
                        )
                    return "ok"
                except ValidationError:
                    return "blocked"
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            return list(pool.map(worker, actions))

    def test_cancel_vs_fulfill_one_transition(self):
        from rentals.models import Loan

        req = self.request_for(self.customer)
        result = self.race(
            [
                ("cancel", req.pk, self.customer.pk),
                ("fulfill", req.pk, self.operator.pk),
            ]
        )
        self.assertCountEqual(result, ["ok", "blocked"])
        req.refresh_from_db()
        self.assertIn(req.status, ["CANCELADA", "ENTREGADA"])
        self.assertEqual(Loan.objects.count(), int(req.status == "ENTREGADA"))

    def test_two_requests_one_active_loan(self):
        from rentals.models import Loan

        other = User.objects.create_user(
            "otro_cliente",
            contractor=Contractor.objects.create(name="Otra", tax_id="DEMO-OTHER"),
        )
        first = self.request_for(self.customer)
        second = self.request_for(other)
        self.assertCountEqual(
            self.race(
                [
                    ("fulfill", first.pk, self.operator.pk),
                    ("fulfill", second.pk, self.operator.pk),
                ]
            ),
            ["ok", "blocked"],
        )
        self.assertEqual(Loan.objects.count(), 1)
