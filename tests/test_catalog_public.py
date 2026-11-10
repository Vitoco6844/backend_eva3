import io
from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.exceptions import ValidationError
from tests.base import DomainCase
from maintenance.models import MaintenancePlan


class CatalogTests(DomainCase):
    def test_public_home_catalog_and_filters(self):
        for path in ["/", "/catalogo/", f"/catalogo/herramientas/{self.asset.pk}/"]:
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 200)
        self.assertContains(self.client.get("/catalogo/?q=Taladro"), "Taladro")
        self.assertNotContains(self.client.get("/catalogo/?q=NoExiste"), "T-001")

    def test_public_projection_hides_operational_data(self):
        self.asset.serial = "SERIE-PRIVADA-482"
        self.asset.save(update_fields=["serial"])
        self.warehouse.name = "BODEGA_PRIVADA_482"
        self.warehouse.save()
        response = self.client.get(f"/catalogo/herramientas/{self.asset.pk}/")
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "SERIE-PRIVADA-482")
        self.assertNotContains(response, "BODEGA_PRIVADA_482")
        self.assertNotContains(response, self.contractor.name)

    def test_unpublished_tools_are_hidden(self):
        self.asset.status = "BAJA"
        self.asset.save(update_fields=["status"])
        self.assertEqual(
            self.client.get(f"/catalogo/herramientas/{self.asset.pk}/").status_code, 404
        )
        self.assertEqual(
            self.client.get(
                f"/catalogo/herramientas/{self.asset.pk}/imagen/"
            ).status_code,
            404,
        )

    def test_due_asset_cannot_be_selected(self):
        from inventory.catalog import available_for_request

        self.assertTrue(available_for_request(self.asset))
        MaintenancePlan.objects.create(asset=self.asset, due_hours=0)
        self.assertFalse(available_for_request(self.asset))

    def test_image_limits_and_formats(self):
        from inventory.validators import validate_tool_image

        for name, size, format in [
            ("fine.png", (60, 40), "PNG"),
            ("wide.png", (4097, 10), "PNG"),
            ("animation.gif", (40, 40), "GIF"),
        ]:
            data = io.BytesIO()
            Image.new("RGB", size, "teal").save(data, format=format)
            file = SimpleUploadedFile(name, data.getvalue())
            if name == "fine.png":
                validate_tool_image(file)
            else:
                with self.subTest(name=name), self.assertRaises(ValidationError):
                    validate_tool_image(file)
        with self.assertRaises(ValidationError):
            validate_tool_image(
                SimpleUploadedFile("large.png", b"x" * (512 * 1024 + 1))
            )
        with self.assertRaises(ValidationError):
            validate_tool_image(SimpleUploadedFile("fake.png", b"not an image"))

    def test_fallback_image_is_available(self):
        response = self.client.get(f"/catalogo/herramientas/{self.asset.pk}/imagen/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/png")
        self.assertTrue(b"".join(response.streaming_content).startswith(b"\x89PNG"))

    def test_invalid_category_is_not_server_error(self):
        self.client.raise_request_exception = False
        self.assertEqual(
            self.client.get("/catalogo/", {"category": "²"}).status_code, 200
        )
        self.assertEqual(
            self.client.get("/catalogo/", {"category": "9" * 5000}).status_code, 200
        )
