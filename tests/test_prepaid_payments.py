from unittest.mock import patch
from django.core.exceptions import ValidationError, PermissionDenied
from django.utils import timezone
from tests.base import DomainCase, signature
from tests.test_prepaid_approval import ApprovalTests
from payments.models import PaymentAttempt


class PrepaidPayments(DomainCase):
    request = ApprovalTests.request
    approve = ApprovalTests.approve

    def paid_request(self):
        from payments.services import start_payment, confirm_payment

        req = self.approve(self.request())
        charge = req.charges.get()
        with patch(
            "payments.services.WebpayGateway.create",
            return_value={
                "token": "prepaid-token",
                "url": "https://webpay3gint.transbank.cl/webpayserver/initTransaction",
            },
        ):
            attempt = start_payment(charge_id=charge.pk, actor=self.customer)
        data = {
            "status": "AUTHORIZED",
            "response_code": 0,
            "buy_order": attempt.order,
            "session_id": str(attempt.session_id),
            "amount": 12000,
            "authorization_code": "1234",
        }
        with patch("payments.services.WebpayGateway.status", return_value=data):
            confirm_payment(attempt.token)
            confirm_payment(attempt.token)
        req.refresh_from_db()
        return req

    def deliver(self, req):
        from rentals.request_services import fulfill_request

        with patch("rentals.services.timezone.now", return_value=req.starts_at):
            return fulfill_request(
                request_id=req.pk,
                actor=self.operator,
                site_id=self.site.pk,
                responsible="Ana",
                due_at=req.ends_at,
                signature=signature(),
            )

    def test_verified_payment_then_delivery_uses_fixed_rate(self):
        req = self.paid_request()
        self.assertEqual(req.status, "PAGADA")
        self.assertIsNone(req.loan_id)
        self.asset.daily_rate = 99999
        self.asset.save()
        loan = self.deliver(req)
        self.assertEqual(loan.billing_mode, "PREPAID")
        self.assertEqual(loan.items.get().daily_rate, 6000)
        self.assertEqual(req.charges.get().loan_id, loan.pk)
        self.assertFalse(req.holds.exists())
        self.assertEqual(self.deliver(req).pk, loan.pk)

    def test_unpaid_or_direct_delivery_is_blocked(self):
        from rentals.services import issue_loan
        from rentals.models import Loan

        req = self.approve(self.request())
        with self.assertRaises(ValidationError):
            self.deliver(req)
        with self.assertRaises(ValidationError):
            issue_loan(
                contractor_id=self.contractor.pk,
                site_id=self.site.pk,
                asset_ids=[self.asset.pk],
                due_at=req.ends_at,
                responsible="Ana",
                signature=signature(),
                actor=self.operator,
            )
        self.assertFalse(Loan.objects.exists())

    def test_voided_initial_cannot_start_payment(self):
        from rentals.request_services import cancel_request
        from payments.services import start_payment

        req = self.approve(self.request())
        cancel_request(request_id=req.pk, actor=self.customer)
        with self.assertRaises(ValidationError):
            start_payment(charge_id=req.charges.get().pk, actor=self.customer)

    def test_paid_request_cannot_cancel_or_change_dates(self):
        from rentals.request_services import cancel_request, fulfill_request
        from datetime import timedelta

        req = self.paid_request()
        with self.assertRaises(ValidationError):
            cancel_request(request_id=req.pk, actor=self.customer)
        with self.assertRaises(ValidationError):
            fulfill_request(
                request_id=req.pk,
                actor=self.operator,
                site_id=self.site.pk,
                responsible="Ana",
                due_at=req.ends_at + timedelta(days=1),
                signature=signature(),
            )

    def test_mismatch_does_not_unlock_delivery(self):
        from payments.services import _apply

        req = self.approve(self.request())
        charge = req.charges.get()
        attempt = PaymentAttempt.objects.create(
            charge=charge, amount=12000, order="wrong", status="PENDING"
        )
        _apply(
            attempt.pk,
            {
                "status": "AUTHORIZED",
                "response_code": 0,
                "buy_order": attempt.order,
                "session_id": str(attempt.session_id),
                "amount": 1,
                "authorization_code": "1234",
            },
        )
        req.refresh_from_db()
        self.assertEqual(req.status, "APROBADA")
        with self.assertRaises(ValidationError):
            self.deliver(req)

    def test_paid_delivery_rechecks_maintenance(self):
        from maintenance.models import MaintenancePlan

        req = self.paid_request()
        MaintenancePlan.objects.create(asset=self.asset, due_at=timezone.now())
        with self.assertRaises(ValidationError):
            self.deliver(req)
        self.assertTrue(req.holds.exists())
        self.assertIsNotNone(req.charges.get().paid_at)
        req.refresh_from_db()
        self.assertIsNone(req.loan_id)
