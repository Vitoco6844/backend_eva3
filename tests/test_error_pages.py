from django.test import override_settings
from tests.base import DomainCase


@override_settings(DEBUG=False)
class ErrorPageTests(DomainCase):
    def test_guest_404_has_home_button(self):
        response = self.client.get("/esta-pagina-no-existe/")
        self.assertContains(response, "Página no encontrada", status_code=404)
        self.assertContains(response, "Volver al inicio", status_code=404)
        self.assertContains(response, 'href="/"', status_code=404)

    def test_authenticated_404_has_home_button(self):
        self.client.force_login(self.customer)
        response = self.client.get("/otra-pagina-no-existe/")
        self.assertContains(response, "Volver al inicio", status_code=404)

    def test_unknown_api_route_returns_json(self):
        response = self.client.get("/api/unknown-resource/")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response["Content-Type"], "application/json")
