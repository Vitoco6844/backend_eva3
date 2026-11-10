import uuid
from datetime import timedelta
from django.utils import timezone
from django.core.exceptions import ValidationError, PermissionDenied
from tests.base import DomainCase


class ApprovalTests(DomainCase):
    def request(self):
        from rentals.request_services import submit_request

        now = timezone.now() + timedelta(hours=1)
        self.asset.daily_rate = 6000
        self.asset.save()
        return submit_request(
            actor=self.customer,
            asset_ids=[self.asset.pk],
            site_name="Obra",
            site_address="Dirección",
            responsible="Ana",
            starts_at=now,
            ends_at=now + timedelta(days=2),
            notes="",
            submit_key=uuid.uuid4(),
        )

    def approve(self, req):
        from rentals.approval_services import approve_request, approval_quote

        return approve_request(
            request_id=req.pk,
            site_id=self.site.pk,
            quote=approval_quote(req, self.operator),
            actor=self.operator,
        )

    def test_approve_holds_without_loan_and_freezes_price(self):
        from payments.models import Charge
        from rentals.models import Loan, AssetHold
        from inventory.catalog import available_for_request

        req = self.approve(self.request())
        self.assertEqual(req.status, "APROBADA")
        self.assertEqual(req.approved_amount, 12000)
        self.assertEqual(Charge.objects.get(rental_request=req).amount, 12000)
        self.assertEqual(Charge.objects.get(rental_request=req).kind, "INITIAL")
        self.assertEqual(AssetHold.objects.get().request_id, req.pk)
        self.assertFalse(available_for_request(self.asset))
        self.assertEqual(Loan.objects.count(), 0)
        self.approve(req)
        self.assertEqual(Charge.objects.count(), 1)

    def test_cancel_voids_charge_and_releases_hold(self):
        from rentals.request_services import cancel_request
        from rentals.models import AssetHold

        req = self.approve(self.request())
        cancel_request(request_id=req.pk, actor=self.customer)
        self.assertFalse(AssetHold.objects.exists())
        self.assertIsNotNone(req.charges.get().voided_at)

    def test_active_or_uncertain_attempt_prevents_cancel(self):
        from rentals.request_services import cancel_request
        from payments.models import PaymentAttempt

        req = self.approve(self.request())
        charge = req.charges.get()
        PaymentAttempt.objects.create(
            charge=charge, amount=charge.amount, order="uncertain", status="UNKNOWN"
        )
        with self.assertRaises(ValidationError):
            cancel_request(request_id=req.pk, actor=self.customer)
        self.assertTrue(req.holds.exists())

    def test_changed_quote_or_customer_cannot_approve(self):
        from rentals.approval_services import approve_request, approval_quote

        req = self.request()
        quote = approval_quote(req, self.operator)
        self.asset.daily_rate = 7000
        self.asset.save()
        with self.assertRaises(ValidationError):
            approve_request(
                request_id=req.pk,
                site_id=self.site.pk,
                quote=quote,
                actor=self.operator,
            )
        with self.assertRaises(PermissionDenied):
            approve_request(
                request_id=req.pk,
                site_id=self.site.pk,
                quote=quote,
                actor=self.customer,
            )

    def test_held_asset_cannot_transfer_retire_or_start_maintenance(self):
        from inventory.services import transfer_asset, retire_asset
        from inventory.models import Warehouse
        from maintenance.services import start_maintenance

        self.approve(self.request())
        target = Warehouse.objects.create(name="Otra", site=self.site)
        for fn, kw in [
            (
                transfer_asset,
                dict(asset_id=self.asset.pk, warehouse_id=target.pk, reason="Mover"),
            ),
            (retire_asset, dict(asset_id=self.asset.pk, reason="Baja")),
            (start_maintenance, dict(asset_id=self.asset.pk, notes="Trabajo")),
        ]:
            with self.assertRaises(ValidationError):
                fn(actor=self.operator, **kw)

    def test_held_category_cannot_change_via_model_validation_or_api(self):
        from inventory.models import Category

        req = self.approve(self.request())
        other = Category.objects.create(name="Otra")
        self.asset.category = other
        with self.assertRaises(ValidationError):
            self.asset.full_clean()
        self.client.force_login(self.operator)
        response = self.client.patch(
            f"/api/assets/{self.asset.pk}/",
            {"category": other.pk},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
