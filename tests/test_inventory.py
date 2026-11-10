from django.core.exceptions import ValidationError
from tests.base import DomainCase
from inventory.models import Warehouse, AssetEvent
from inventory.services import transfer_asset, retire_asset


class InventoryTests(DomainCase):
    def test_transfer_creates_event(self):
        target = Warehouse.objects.create(name="Destino", site=self.site)
        transfer_asset(
            asset_id=self.asset.pk,
            warehouse_id=target.pk,
            actor=self.operator,
            reason="Cambio de bodega",
        )
        event = AssetEvent.objects.get()
        self.assertEqual(event.origin_id, self.warehouse.pk)
        self.assertEqual(event.destination_id, target.pk)

    def test_retire_protects_history(self):
        retire_asset(
            asset_id=self.asset.pk, actor=self.operator, reason="Fin de vida útil"
        )
        with self.assertRaises(ValidationError):
            self.issue()

    def test_api_permissions_and_direct_state_edit(self):
        self.client.force_login(self.customer)
        self.assertEqual(self.client.get("/api/assets/").status_code, 403)
        self.client.force_login(self.operator)
        response = self.client.patch(
            f"/api/assets/{self.asset.pk}/",
            data='{"status":"BAJA"}',
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.asset.refresh_from_db()
        self.assertEqual(self.asset.status, "DISPONIBLE")

    def test_category_crud(self):
        self.client.force_login(self.operator)
        response = self.client.post("/api/categories/", {"name": "Nueva categoría"})
        self.assertEqual(response.status_code, 201)
        pk = response.json()["id"]
        response = self.client.patch(
            f"/api/categories/{pk}/",
            data='{"name":"Actualizada"}',
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        response = self.client.get(f"/api/categories/{pk}/")
        self.assertEqual(response.json()["name"], "Actualizada")
        self.assertEqual(self.client.delete(f"/api/categories/{pk}/").status_code, 204)

    def test_contractor_mutation_requires_administrator(self):
        self.client.force_login(self.operator)
        self.assertEqual(
            self.client.post(
                "/api/contractors/", {"name": "No permitido", "tax_id": "NEW"}
            ).status_code,
            403,
        )

    def test_used_category_cannot_be_deleted(self):
        self.client.force_login(self.operator)
        self.assertEqual(
            self.client.delete(f"/api/categories/{self.category.pk}/").status_code, 409
        )

    def test_unknown_update_is_not_a_server_error(self):
        self.client.force_login(self.operator)
        self.client.raise_request_exception = False
        response = self.client.patch(
            "/api/categories/999999/",
            data='{"name":"No existe"}',
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 404)
