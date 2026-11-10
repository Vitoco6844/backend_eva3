from django.test import Client
from tests.base import DomainCase


class WebTests(DomainCase):
    def test_dashboard_by_role(self):
        self.assertEqual(self.client.get("/").status_code, 302)
        self.client.force_login(self.operator)
        for path in [
            "/",
            "/inventory/assets/",
            "/inventory/contractors/",
            "/rentals/",
            "/maintenance/",
            "/alerts/",
            "/payments/",
        ]:
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 200)
        self.client.force_login(self.customer)
        self.assertEqual(self.client.get("/inventory/assets/").status_code, 403)
        self.assertEqual(self.client.get("/rentals/").status_code, 200)

    def test_private_signature(self):
        from accounts.models import User

        loan = self.issue()
        sig = loan.signatures.get()
        other = User.objects.create_user("otro", password="OtraClaveSegura123")
        self.client.force_login(other)
        self.assertEqual(self.client.get(f"/signatures/{sig.pk}/").status_code, 404)

    def test_session_requires_csrf(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.operator)
        self.assertEqual(
            client.post("/inventory/categories/new/", {"name": "Nueva"}).status_code,
            403,
        )

    def test_forms_and_detail_pages_render(self):
        self.client.force_login(self.operator)
        loan = self.issue()
        for path in [
            "/rentals/new/",
            f"/rentals/{loan.pk}/",
            f"/rentals/{loan.pk}/return/",
            f"/inventory/assets/{self.asset.pk}/",
            "/inventory/assets/new/",
            f"/inventory/assets/{self.asset.pk}/edit/",
            "/maintenance/plan/",
            "/maintenance/start/",
        ]:
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 200)

    def test_return_validation_preserves_form(self):
        loan = self.issue()
        self.client.force_login(self.operator)
        response = self.client.post(
            f"/rentals/{loan.pk}/return/", {"signature": "invalid"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "firma válida")
        loan.refresh_from_db()
        self.assertIsNone(loan.closed_at)

    def test_foreign_loan_and_charge_not_listed(self):
        from inventory.models import Contractor
        from accounts.models import User
        from rentals.services import return_items
        from tests.base import signature

        loan = self.issue()
        return_items(
            loan_id=loan.pk,
            items=[{"item_id": loan.items.get().pk, "usage_hours": 0}],
            signature=signature(),
            actor=self.operator,
        )
        other = Contractor.objects.create(name="Ajeno", tax_id="AJENO")
        user = User.objects.create_user("ajeno", contractor=other)
        self.client.force_login(user)
        self.assertEqual(self.client.get(f"/rentals/{loan.pk}/").status_code, 404)
        self.assertEqual(
            self.client.get(f"/payments/{loan.charge.pk}/").status_code, 404
        )
        self.assertEqual(self.client.get("/api/loans/").json()["count"], 0)
        self.assertEqual(self.client.get("/api/charges/").json()["count"], 0)
