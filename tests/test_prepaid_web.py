from tests.base import DomainCase, signature
from tests import test_prepaid_payments as helpers


class PrepaidWeb(DomainCase):
    request = helpers.PrepaidPayments.request
    approve = helpers.PrepaidPayments.approve
    paid_request = helpers.PrepaidPayments.paid_request

    def test_approval_and_initial_payment_visible(self):
        req = self.request()
        self.client.force_login(self.operator)
        self.assertEqual(
            self.client.get(f"/solicitudes/{req.pk}/aprobar/").status_code, 200
        )
        req = self.approve(req)
        self.client.force_login(self.customer)
        response = self.client.get(f"/mis-solicitudes/{req.pk}/")
        self.assertContains(response, "Pagar período contratado")
        self.assertContains(response, "devolución anticipada")
        charge = req.charges.get()
        self.assertContains(
            self.client.get(f"/payments/{charge.pk}/"), "Período contratado"
        )

    def test_unpaid_forced_web_and_api_delivery_cannot_bypass(self):
        req = self.approve(self.request())
        self.client.force_login(self.operator)
        response = self.client.post(
            f"/solicitudes/{req.pk}/entregar/",
            {"responsible": "Ana", "signature": signature()},
        )
        self.assertEqual(response.status_code, 302)
        from rentals.models import Loan

        self.assertFalse(Loan.objects.exists())
        response = self.client.post(
            "/api/loans/",
            {
                "contractor_id": self.contractor.pk,
                "site_id": self.site.pk,
                "asset_ids": [self.asset.pk],
                "responsible": "Ana",
                "due_at": req.ends_at.isoformat(),
                "signature": signature(),
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Loan.objects.exists())

    def test_operator_can_prepare_request_and_foreign_charge_is_hidden(self):
        self.client.force_login(self.operator)
        self.assertEqual(self.client.get("/solicitudes/nueva/").status_code, 200)
        self.assertRedirects(self.client.get("/rentals/new/"), "/solicitudes/nueva/")
        req = self.approve(self.request())
        from accounts.models import User

        other = User.objects.create_user("other", password="NoCompartir.123")
        self.client.force_login(other)
        self.assertEqual(
            self.client.get(f"/payments/{req.charges.get().pk}/").status_code, 404
        )

    def test_operator_initial_dates_are_local_not_utc(self):
        from datetime import datetime, timedelta, timezone as dt_timezone
        from unittest.mock import patch
        from django.utils import timezone

        fixed = datetime(2026, 11, 10, 15, 0, tzinfo=dt_timezone.utc)
        self.client.force_login(self.operator)
        with patch("django.utils.timezone.now", return_value=fixed):
            response = self.client.get("/solicitudes/nueva/")
        self.assertEqual(
            response.context["form"].initial["starts_at"],
            (timezone.localtime(fixed) + timedelta(minutes=2)).strftime(
                "%Y-%m-%dT%H:%M"
            ),
        )
