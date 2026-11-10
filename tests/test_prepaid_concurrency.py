from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import patch
from django.test import TransactionTestCase
from django.db import close_old_connections
from django.core.exceptions import ValidationError
from tests.base import DomainCase
from tests import test_prepaid_payments as helpers


class PrepaidConcurrency(TransactionTestCase):
    setUp = DomainCase.setUp
    request = helpers.PrepaidPayments.request
    approve = helpers.PrepaidPayments.approve
    paid_request = helpers.PrepaidPayments.paid_request
    deliver = helpers.PrepaidPayments.deliver

    def race(self, actions):
        barrier = Barrier(len(actions))

        def run(action):
            close_old_connections()
            try:
                barrier.wait(timeout=15)
                try:
                    action()
                    return "ok"
                except ValidationError:
                    return "blocked"
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=len(actions)) as pool:
            return list(pool.map(run, actions))

    def test_competing_approvals_retain_once(self):
        from rentals.models import AssetHold, Loan

        first = self.request()
        second = self.request()
        self.assertCountEqual(
            self.race([lambda: self.approve(first), lambda: self.approve(second)]),
            ["ok", "blocked"],
        )
        self.assertEqual(AssetHold.objects.count(), 1)
        self.assertEqual(Loan.objects.count(), 0)

    def test_cancel_races_payment_creation_without_releasing_active_payment(self):
        from rentals.request_services import cancel_request
        from payments.services import start_payment
        from rentals.models import AssetHold

        req = self.approve(self.request())
        charge = req.charges.get()
        with patch(
            "payments.services.WebpayGateway.create",
            return_value={
                "token": "race-token",
                "url": "https://webpay3gint.transbank.cl/webpayserver/initTransaction",
            },
        ):
            result = self.race(
                [
                    lambda: cancel_request(request_id=req.pk, actor=self.customer),
                    lambda: start_payment(charge_id=charge.pk, actor=self.customer),
                ]
            )
        self.assertCountEqual(result, ["ok", "blocked"])
        req.refresh_from_db()
        charge.refresh_from_db()
        if req.status == "CANCELADA":
            self.assertIsNotNone(charge.voided_at)
            self.assertFalse(AssetHold.objects.exists())
            self.assertFalse(charge.attempts.exists())
        else:
            self.assertEqual(req.status, "APROBADA")
            self.assertTrue(AssetHold.objects.exists())
            self.assertEqual(charge.attempts.count(), 1)

    def test_two_deliveries_create_single_loan(self):
        from rentals.request_services import fulfill_request
        from rentals.models import Loan
        from tests.base import signature

        req = self.paid_request()
        with patch("rentals.services.timezone.now", return_value=req.starts_at):
            result = self.race(
                [
                    lambda: fulfill_request(
                        request_id=req.pk,
                        signature=signature(),
                        responsible="Ana",
                        actor=self.operator,
                    )
                ]
                * 2
            )
        self.assertEqual(result, ["ok", "ok"])
        self.assertEqual(Loan.objects.count(), 1)
