from datetime import timedelta
from unittest import skipUnless
from uuid import uuid4

from django.conf import settings

from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import User
from inventory.models import Site
from rentals.models import Loan
from tests.base import DomainCase, signature


@skipUnless(settings.ROOT_URLCONF == "buildcorp.eva4_urls", "Usa los ajustes de EVA 4.")
@override_settings(ROOT_URLCONF="buildcorp.eva4_urls")
class Eva4IntegrationTests(DomainCase):
    def setUp(self):
        super().setUp()
        self.api = APIClient()
        self.admin = User.objects.create_superuser(
            "eva4admin", password="BuildCorp.test.634"
        )

    def login(self, user="eva4admin", password="BuildCorp.test.634"):
        response = self.api.post(
            "/api/auth/token/", {"username": user, "password": password}, format="json"
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.api.credentials(HTTP_AUTHORIZATION="Bearer " + response.data["access"])
        return response.data

    def test_overview_reports_inventory_and_open_loans_for_staff(self):
        self.assertEqual(self.api.get("/api/overview/").status_code, 401)
        self.login()
        response = self.api.get("/api/overview/")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["available"], 1)
        self.assertEqual(response.data["open_count"], 0)
        self.assertEqual(response.data["loans"], [])

    def test_jwt_and_crud(self):
        self.assertEqual(self.api.get("/api/sites/").status_code, 401)
        self.assertEqual(self.api.get("/cuenta/registro/").status_code, 404)
        self.assertEqual(self.api.get("/catalogo/").status_code, 404)
        self.login()
        created = self.api.post(
            "/api/sites/",
            {"name": "Obra de prueba", "address": "Dirección"},
            format="json",
        )
        self.assertEqual(created.status_code, 201, created.data)
        pk = created.data["id"]
        url = f"/api/sites/{pk}/"
        self.assertEqual(self.api.get(url).data["name"], "Obra de prueba")
        self.assertEqual(
            self.api.patch(url, {"name": "Obra nueva"}, format="json").status_code, 200
        )
        self.assertTrue(Site.objects.filter(pk=pk, name="Obra nueva").exists())
        self.assertEqual(self.api.delete(url).status_code, 204)

    def test_roles_and_token_refresh(self):
        response = self.api.post(
            "/api/auth/token/",
            {"username": "cliente", "password": "ClaveLocalSegura.123"},
            format="json",
        )
        self.assertEqual(response.status_code, 403, response.data)
        tokens = self.login("bodega", "ClaveLocalSegura.123")
        self.assertEqual(self.api.get("/api/users/").status_code, 403)
        self.assertEqual(
            self.api.delete(f"/api/categories/{self.category.pk}/").status_code, 403
        )
        self.assertEqual(self.api.get("/api/auth/me/").data["role"], "BODEGUERO")
        response = self.api.post(
            "/api/auth/refresh/", {"refresh": tokens["refresh"]}, format="json"
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.operator.is_active = False
        self.operator.save(update_fields=["is_active"])
        self.assertEqual(self.api.get("/api/auth/me/").status_code, 401)

    def test_internal_approval_delivery_return_and_alerts(self):
        self.login()
        start = timezone.now() + timedelta(minutes=5)
        created = self.api.post(
            "/api/rental-requests/",
            {
                "contractor_id": self.contractor.pk,
                "asset_ids": [self.asset.pk],
                "site_name": self.site.name,
                "site_address": self.site.address,
                "responsible": "Responsable",
                "starts_at": start.isoformat(),
                "ends_at": (start + timedelta(days=2)).isoformat(),
                "submit_key": str(uuid4()),
            },
            format="json",
        )
        self.assertEqual(created.status_code, 201, created.data)
        self.assertTrue(created.data["internal"])
        root = f"/api/rental-requests/{created.data['id']}/"
        quote = self.api.get(root + "approval-quote/").data["quote"]
        response = self.api.post(
            root + "approve/", {"site_id": self.site.pk, "quote": quote}, format="json"
        )
        self.assertEqual(response.status_code, 200, response.data)
        data = {"responsible": "Responsable", "signature": signature()}
        self.assertEqual(
            self.api.post(root + "fulfill/", data, format="json").status_code, 400
        )
        from unittest.mock import patch

        with patch(
            "rentals.request_services.timezone.now",
            return_value=start + timedelta(minutes=1),
        ):
            delivered = self.api.post(root + "fulfill/", data, format="json")
        self.assertEqual(delivered.status_code, 200, delivered.data)
        loan = Loan.objects.get(pk=delivered.data["loan"])
        self.assertEqual(loan.billing_mode, "INTERNAL")
        response = self.api.post(
            f"/api/loans/{loan.pk}/return/",
            {
                "signature": signature(),
                "items": [{"item_id": loan.items.get().pk, "usage_hours": "1.50"}],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        loan.refresh_from_db()
        self.assertIsNotNone(loan.closed_at)
        self.assertFalse(loan.charges.exists())
        self.assertEqual(self.api.get("/api/alerts/").status_code, 200)
