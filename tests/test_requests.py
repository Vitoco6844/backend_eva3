import uuid
from datetime import timedelta
from django.utils import timezone
from django.core.exceptions import ValidationError, PermissionDenied
from tests.base import DomainCase, signature
from inventory.models import Asset, Contractor
from accounts.models import User


class RequestTests(DomainCase):
    def data(self, **changes):
        start = timezone.now() + timedelta(days=1)
        data = dict(
            actor=self.customer,
            asset_ids=[self.asset.pk],
            site_name="Obra cliente",
            site_address="Dirección solicitada",
            responsible="Ana Rojas",
            starts_at=start,
            ends_at=start + timedelta(days=1),
            notes="",
            submit_key=uuid.uuid4(),
        )
        data.update(changes)
        return data

    def submit(self, **changes):
        from rentals.request_services import submit_request

        return submit_request(**self.data(**changes))

    def test_submission_does_not_reserve_or_charge(self):
        from rentals.models import Loan
        from payments.models import Charge, PaymentAttempt

        req = self.submit()
        self.assertEqual(req.status, "PENDIENTE")
        self.assertEqual(req.estimated_amount, 1000)
        self.asset.refresh_from_db()
        self.assertEqual(self.asset.status, "DISPONIBLE")
        self.assertEqual(Loan.objects.count(), 0)
        self.assertEqual(Charge.objects.count(), 0)
        self.assertEqual(PaymentAttempt.objects.count(), 0)

    def test_server_recomputes_estimate_and_rounding(self):
        other = Asset.objects.create(
            code="OTRO",
            name="Otro",
            category=self.category,
            warehouse=self.warehouse,
            daily_rate=2000,
        )
        data = self.data(asset_ids=[self.asset.pk, other.pk])
        req = self.submit(**{k: v for k, v in data.items() if k != "actor"})
        self.assertEqual(req.estimated_amount, 3000)
        data["ends_at"] += timedelta(seconds=1)
        data["submit_key"] = uuid.uuid4()
        from rentals.request_services import submit_request

        self.assertEqual(submit_request(**data).estimated_amount, 6000)

    def test_duplicate_submission_is_idempotent(self):
        from rentals.request_services import submit_request

        data = self.data()
        first = submit_request(**data)
        second = submit_request(**data)
        self.assertEqual(first.pk, second.pk)
        data["notes"] = "Contenido cambiado"
        with self.assertRaises(ValidationError):
            submit_request(**data)

    def test_empty_or_invalid_dates_rejected(self):
        now = timezone.now()
        for changes in [
            {"asset_ids": []},
            {"starts_at": now - timedelta(days=1)},
            {"ends_at": now},
            {"asset_ids": [self.asset.pk, self.asset.pk]},
        ]:
            with self.subTest(changes=changes), self.assertRaises(ValidationError):
                self.submit(**changes)

    def test_blocked_customer_cannot_submit(self):
        self.contractor.manual_block = True
        self.contractor.save(update_fields=["manual_block"])
        with self.assertRaises(ValidationError):
            self.submit()

    def test_guest_selection_survives_authentication(self):
        response = self.client.post(f"/mi-solicitud/agregar/{self.asset.pk}/")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.session["rental_selection"], [self.asset.pk])
        response = self.client.post("/mi-solicitud/enviar/", {})
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response["Location"])
        self.client.force_login(self.customer)
        self.assertEqual(self.client.session["rental_selection"], [self.asset.pk])

    def test_only_own_pending_request_can_be_cancelled(self):
        from rentals.request_services import cancel_request

        req = self.submit()
        other = User.objects.create_user(
            "otro_cliente",
            contractor=Contractor.objects.create(name="Otra", tax_id="DEMO-OTHER"),
        )
        with self.assertRaises(PermissionDenied):
            cancel_request(request_id=req.pk, actor=other)
        result = cancel_request(request_id=req.pk, actor=self.customer)
        self.assertEqual(result.status, "CANCELADA")

    def test_customer_cannot_resolve_and_rejection_requires_reason(self):
        from rentals.request_services import reject_request, fulfill_request

        req = self.submit()
        with self.assertRaises(PermissionDenied):
            reject_request(request_id=req.pk, reason="No", actor=self.customer)
        with self.assertRaises(ValidationError):
            reject_request(request_id=req.pk, reason="", actor=self.operator)
        req = reject_request(
            request_id=req.pk, reason="No hay disponibilidad", actor=self.operator
        )
        self.assertEqual(req.status, "RECHAZADA")

    def test_fulfill_is_signed_and_idempotent(self):
        from rentals.request_services import fulfill_request
        from rentals.models import Loan

        req = self.submit()
        data = dict(
            request_id=req.pk,
            site_id=self.site.pk,
            responsible="Ana",
            due_at=req.ends_at,
            signature=signature(),
            actor=self.operator,
        )
        loan = fulfill_request(**data)
        again = fulfill_request(**data)
        self.assertEqual(loan.pk, again.pk)
        self.assertEqual(Loan.objects.count(), 1)
        self.assertEqual(loan.signatures.count(), 1)
        req.refresh_from_db()
        self.assertEqual(req.status, "ENTREGADA")
        self.assertEqual(req.loan_id, loan.pk)

    def test_fulfill_failure_rolls_back(self):
        from rentals.request_services import fulfill_request
        from rentals.models import Loan

        req = self.submit()
        with self.assertRaises(ValidationError):
            fulfill_request(
                request_id=req.pk,
                site_id=self.site.pk,
                responsible="Ana",
                due_at=req.ends_at,
                signature="invalid",
                actor=self.operator,
            )
        req.refresh_from_db()
        self.assertEqual(req.status, "PENDIENTE")
        self.assertEqual(Loan.objects.count(), 0)

    def test_foreign_request_is_hidden(self):
        req = self.submit()
        other = User.objects.create_user(
            "otro_cliente",
            contractor=Contractor.objects.create(name="Otra", tax_id="DEMO-OTHER"),
        )
        self.client.force_login(other)
        self.assertEqual(
            self.client.get(f"/mis-solicitudes/{req.pk}/").status_code, 404
        )

    def test_api_rejects_client_controlled_amount_or_identity(self):
        self.client.force_login(self.customer)
        data = self.data()
        data.pop("actor")
        data["estimated_amount"] = 1
        response = self.client.post(
            "/api/rental-requests/", data, content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)
        from rentals.models import RentalRequest

        self.assertEqual(RentalRequest.objects.count(), 0)

    def test_double_web_submission_keeps_same_request(self):
        self.client.post(f"/mi-solicitud/agregar/{self.asset.pk}/")
        self.client.force_login(self.customer)
        self.assertEqual(self.client.get("/mi-solicitud/").status_code, 200)
        data = self.data()
        data.pop("actor")
        data["submit_key"] = self.client.session["rental_submit_key"]
        first = self.client.post("/mi-solicitud/enviar/", data)
        second = self.client.post("/mi-solicitud/enviar/", data)
        self.assertEqual(first.status_code, 302)
        self.assertEqual(first["Location"], second["Location"])
        from rentals.models import RentalRequest

        self.assertEqual(RentalRequest.objects.count(), 1)

    def test_changed_delivery_rate_requires_new_acceptance(self):
        from rentals.request_services import delivery_quote, fulfill_request
        from rentals.models import Loan

        req = self.submit()
        quote = delivery_quote(req, self.operator)
        self.asset.daily_rate = 9000
        self.asset.save(update_fields=["daily_rate"])
        with self.assertRaises(ValidationError):
            fulfill_request(
                request_id=req.pk,
                site_id=self.site.pk,
                responsible="Ana",
                due_at=req.ends_at,
                signature=signature(),
                actor=self.operator,
                quote=quote,
            )
        self.assertEqual(Loan.objects.count(), 0)
        req.refresh_from_db()
        self.assertEqual(req.status, "PENDIENTE")

    def test_unpublished_selection_can_be_cleared(self):
        extra = Asset.objects.bulk_create(
            [
                Asset(
                    code=f"EXTRA-{i}",
                    name=f"Herramienta {i}",
                    category=self.category,
                    warehouse=self.warehouse,
                    daily_rate=1000,
                )
                for i in range(19)
            ]
        )
        session = self.client.session
        session["rental_selection"] = [self.asset.pk] + [a.pk for a in extra]
        session.save()
        self.category.active = False
        self.category.save(update_fields=["active"])
        response = self.client.get("/mi-solicitud/")
        self.assertContains(response, "Vaciar selección")
        self.client.post("/mi-solicitud/vaciar/")
        self.assertEqual(self.client.session["rental_selection"], [])

    def test_estimate_counts_actual_24h_periods_across_dst(self):
        from datetime import datetime
        from zoneinfo import ZoneInfo
        from rentals.request_services import _days

        zone = ZoneInfo("America/Santiago")
        self.assertEqual(
            _days(
                datetime(2026, 4, 4, 12, tzinfo=zone),
                datetime(2026, 4, 5, 12, tzinfo=zone),
            ),
            2,
        )
