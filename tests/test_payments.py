from unittest.mock import patch
from django.core.exceptions import ValidationError, PermissionDenied
from tests.base import DomainCase, signature
from rentals.services import return_items
from payments.models import PaymentAttempt


class PaymentTests(DomainCase):
    def charge(self):
        loan = self.issue()
        return_items(
            loan_id=loan.pk,
            items=[{"item_id": loan.items.get().pk, "usage_hours": 2}],
            signature=signature(),
            actor=self.operator,
        )
        return loan.charge

    def response(self, attempt, **changes):
        data = {
            "status": "AUTHORIZED",
            "response_code": 0,
            "buy_order": attempt.order,
            "session_id": str(attempt.session_id),
            "amount": attempt.amount,
            "authorization_code": "1213",
        }
        data.update(changes)
        return data

    def attempt(self):
        from payments.services import start_payment

        with patch(
            "payments.services.WebpayGateway.create",
            return_value={
                "token": "test-token",
                "url": "https://webpay3gint.transbank.cl/webpayserver/initTransaction",
            },
        ):
            return start_payment(charge_id=self.charge().pk, actor=self.customer)

    def test_approved_and_duplicate_return(self):
        from payments.services import confirm_payment

        attempt = self.attempt()
        with patch(
            "payments.services.WebpayGateway.status",
            return_value=self.response(attempt),
        ):
            confirm_payment(attempt.token)
            confirm_payment(attempt.token)
        attempt.charge.refresh_from_db()
        self.assertIsNotNone(attempt.charge.paid_at)
        self.assertEqual(PaymentAttempt.objects.count(), 1)

    def test_amount_mismatch(self):
        from payments.services import confirm_payment

        attempt = self.attempt()
        with patch(
            "payments.services.WebpayGateway.status",
            return_value=self.response(attempt, amount=1),
        ):
            result = confirm_payment(attempt.token)
        self.assertEqual(result.status, "UNKNOWN")
        attempt.charge.refresh_from_db()
        self.assertIsNone(attempt.charge.paid_at)

    def test_rejected(self):
        from payments.services import confirm_payment

        attempt = self.attempt()
        with patch(
            "payments.services.WebpayGateway.status",
            return_value=self.response(attempt, status="FAILED", response_code=-1),
        ):
            result = confirm_payment(attempt.token)
        self.assertEqual(result.status, "REJECTED")

    def test_timeout_requires_reconciliation(self):
        from payments.services import confirm_payment, start_payment

        attempt = self.attempt()
        with patch("payments.services.WebpayGateway.status", side_effect=TimeoutError):
            result = confirm_payment(attempt.token)
        self.assertEqual(result.status, "UNKNOWN")
        with self.assertRaises(ValidationError):
            start_payment(charge_id=attempt.charge_id, actor=self.customer)

    def test_foreign_charge(self):
        from payments.services import start_payment
        from accounts.models import User

        other = User.objects.create_user("ajeno", password="ClaveSegura123")
        with self.assertRaises(PermissionDenied):
            start_payment(charge_id=self.charge().pk, actor=other)

    def test_unknown_token(self):
        from payments.services import confirm_payment

        with self.assertRaises(ValidationError):
            confirm_payment("unknown")

    def test_sessionless_return(self):
        attempt = self.attempt()
        with patch(
            "payments.services.WebpayGateway.status",
            return_value=self.response(attempt),
        ):
            response = self.client.post(
                "/payments/return/", {"token_ws": attempt.token}
            )
        self.assertEqual(response.status_code, 302)
        attempt.charge.refresh_from_db()
        self.assertIsNotNone(attempt.charge.paid_at)

    def test_commit_initialized_transaction(self):
        from payments.services import confirm_payment

        attempt = self.attempt()
        with (
            patch(
                "payments.services.WebpayGateway.status",
                return_value={"status": "INITIALIZED"},
            ),
            patch(
                "payments.services.WebpayGateway.commit",
                return_value=self.response(attempt),
            ),
        ):
            result = confirm_payment(attempt.token)
        self.assertEqual(result.status, "APPROVED")

    def test_cancelled(self):
        from payments.services import reconcile_payment

        attempt = self.attempt()
        with patch(
            "payments.services.WebpayGateway.status",
            return_value=self.response(attempt, status="REVERSED", response_code=-1),
        ):
            result = reconcile_payment(attempt.pk)
        self.assertEqual(result.status, "CANCELLED")
        attempt.charge.refresh_from_db()
        self.assertIsNone(attempt.charge.paid_at)

    def test_expired(self):
        from payments.services import reconcile_payment

        attempt = self.attempt()
        with patch(
            "payments.services.WebpayGateway.status",
            return_value=self.response(attempt, status="EXPIRED", response_code=-1),
        ):
            result = reconcile_payment(attempt.pk)
        self.assertEqual(result.status, "EXPIRED")

    def test_session_mismatch(self):
        from payments.services import confirm_payment

        attempt = self.attempt()
        with patch(
            "payments.services.WebpayGateway.status",
            return_value=self.response(attempt, session_id="otra"),
        ):
            result = confirm_payment(attempt.token)
        self.assertEqual(result.status, "UNKNOWN")
        attempt.charge.refresh_from_db()
        self.assertIsNone(attempt.charge.paid_at)

    def test_create_timeout_is_not_retried(self):
        from payments.services import start_payment

        charge = self.charge()
        with patch("payments.services.WebpayGateway.create", side_effect=TimeoutError):
            result = start_payment(charge_id=charge.pk, actor=self.customer)
        self.assertEqual(result.status, "UNKNOWN")
        self.assertIsNone(result.token)
        with self.assertRaises(ValidationError):
            start_payment(charge_id=charge.pk, actor=self.customer)

    def test_cancel_callback_does_not_trust_browser(self):
        attempt = self.attempt()
        with patch(
            "payments.services.WebpayGateway.status",
            return_value={"status": "INITIALIZED"},
        ):
            response = self.client.post(
                "/payments/return/", {"TBK_TOKEN": attempt.token}
            )
        self.assertEqual(response.status_code, 302)
        attempt.refresh_from_db()
        self.assertEqual(attempt.status, "UNKNOWN")

    def test_charge_list_newest_first(self):
        first = self.charge()
        last = self.charge()
        self.client.force_login(self.customer)
        rows = self.client.get("/api/charges/").json()["results"]
        self.assertEqual(rows[0]["id"], last.pk)

    def test_initialized_reconcile_keeps_continue(self):
        from payments.services import reconcile_payment

        attempt = self.attempt()
        initialized = self.response(
            attempt, status="INITIALIZED", response_code=None, authorization_code=""
        )
        with patch("payments.services.WebpayGateway.status", return_value=initialized):
            result = reconcile_payment(attempt.pk)
        self.assertEqual(result.status, "PENDING")
        self.client.force_login(self.customer)
        self.assertEqual(
            self.client.get(f"/payments/{attempt.charge_id}/continue/").status_code, 200
        )
        self.assertEqual(PaymentAttempt.objects.count(), 1)

    def test_pending_charge_has_resume_link(self):
        attempt = self.attempt()
        self.client.force_login(self.customer)
        response = self.client.get(f"/payments/{attempt.charge_id}/")
        self.assertContains(response, "Continuar pago de prueba")
