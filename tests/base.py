import base64, io
from PIL import Image, ImageDraw
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from accounts.models import User
from inventory.models import Contractor, Site, Warehouse, Category, Asset


def signature():
    im = Image.new("RGB", (160, 70), "white")
    ImageDraw.Draw(im).line(
        [(10, 40), (50, 10), (85, 50), (140, 20)], fill="black", width=3
    )
    f = io.BytesIO()
    im.save(f, format="PNG")
    return "data:image/png;base64," + base64.b64encode(f.getvalue()).decode()


class DomainCase(TestCase):
    def setUp(self):
        self.operator = User.objects.create_user(
            "bodega", password="ClaveLocalSegura.123", role="BODEGUERO"
        )
        self.contractor = Contractor.objects.create(
            name="Constructora Demo", tax_id="DEMO-1"
        )
        self.customer = User.objects.create_user(
            "cliente", password="ClaveLocalSegura.123", contractor=self.contractor
        )
        self.site = Site.objects.create(name="Obra Norte", address="Dirección ficticia")
        self.warehouse = Warehouse.objects.create(name="Bodega", site=self.site)
        self.category = Category.objects.create(name="Taladros")
        self.asset = Asset.objects.create(
            code="T-001",
            name="Taladro",
            category=self.category,
            warehouse=self.warehouse,
            daily_rate=1000,
        )

    def issue(self, assets=None, **kwargs):
        from rentals.services import issue_loan

        data = dict(
            contractor_id=self.contractor.pk,
            site_id=self.site.pk,
            asset_ids=assets or [self.asset.pk],
            due_at=timezone.now() + timedelta(days=3),
            responsible="Responsable Demo",
            signature=signature(),
            actor=self.operator,
        )
        data.update(kwargs)
        from django.db import transaction
        from unittest.mock import patch
        import uuid
        from rentals.approval_services import (
            create_operator_request,
            approve_request,
            approval_quote,
        )
        from rentals.models import Loan
        from payments.models import Charge

        with transaction.atomic():
            now = timezone.now()
            with patch(
                "rentals.request_services.timezone.now",
                return_value=now - timedelta(minutes=1),
            ):
                req = create_operator_request(
                    contractor_id=data["contractor_id"],
                    actor=data["actor"],
                    asset_ids=data["asset_ids"],
                    site_name="Fixture histórica",
                    site_address="Dirección",
                    responsible=data["responsible"],
                    starts_at=now,
                    ends_at=data["due_at"],
                    notes="Fixture de pruebas",
                    submit_key=uuid.uuid4(),
                )
            req = approve_request(
                request_id=req.pk,
                site_id=data["site_id"],
                quote=approval_quote(req, data["actor"]),
                actor=data["actor"],
            )
            # Fixture bancaria en memoria de tests; los tests específicos verifican el proveedor.
            Charge.objects.filter(rental_request=req).update(paid_at=now)
            req.status = "PAGADA"
            req.save()
            loan = issue_loan(**data, request_id=req.pk)
            Charge.objects.filter(rental_request=req).delete()
            Loan.objects.filter(pk=loan.pk).update(billing_mode="LEGACY_POSTPAID")
            loan.refresh_from_db()
            return loan
