from django.test import TestCase
from django.core.exceptions import ValidationError
from accounts.models import User
from inventory.models import Contractor


class RegistrationTests(TestCase):
    def data(self, **changes):
        values = dict(
            username="ana",
            first_name="Ana",
            last_name="Rojas",
            email="ana@example.test",
            tax_id="12.345.678-5",
            company_name="Obras Ana",
            phone="912345678",
            password="ConstruirSeguro.2026",
        )
        values.update(changes)
        return values

    def test_valid_registration_creates_own_contractor(self):
        from accounts.services import register_customer

        user = register_customer(**self.data())
        self.assertEqual(user.role, "CONTRATISTA")
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertTrue(user.check_password(self.data()["password"]))
        self.assertNotEqual(user.password, self.data()["password"])
        self.assertEqual(user.contractor.tax_id, "12345678-5")
        self.assertEqual(Contractor.objects.count(), 1)
        with self.assertRaises(ValidationError):
            register_customer(**self.data())
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(Contractor.objects.count(), 1)

    def test_invalid_rut_and_password_are_atomic(self):
        from accounts.services import register_customer

        for changes in [
            {"tax_id": "12345678-9"},
            {"password": "123"},
            {"email": "no-email"},
        ]:
            with self.subTest(changes=changes), self.assertRaises(ValidationError):
                register_customer(**self.data(**changes))
        self.assertEqual(User.objects.count(), 0)
        self.assertEqual(Contractor.objects.count(), 0)

    def test_duplicate_normalized_identity_cannot_claim_company(self):
        from accounts.services import register_customer

        existing = Contractor.objects.create(
            name="Empresa existente", tax_id="12.345.678-5", manual_block=True
        )
        with self.assertRaises(ValidationError):
            register_customer(**self.data(tax_id="12345678-5"))
        self.assertEqual(User.objects.count(), 0)
        self.assertEqual(Contractor.objects.get().pk, existing.pk)

    def test_duplicate_email_is_case_insensitive(self):
        from accounts.services import register_customer

        User.objects.create_user("existente", email="ANA@example.test")
        with self.assertRaises(ValidationError):
            register_customer(**self.data())
        self.assertEqual(Contractor.objects.count(), 0)

    def test_registration_logs_in_and_keeps_selection(self):
        session = self.client.session
        session["rental_selection"] = [1, 2]
        session.save()
        data = self.data()
        data["password1"] = data.pop("password")
        data["password2"] = data["password1"]
        response = self.client.post("/cuenta/registro/", data)
        self.assertEqual(response.status_code, 302)
        self.assertIn("_auth_user_id", self.client.session)
        self.assertEqual(self.client.session["rental_selection"], [1, 2])

    def test_privilege_fields_are_rejected(self):
        data = self.data()
        data["password1"] = data.pop("password")
        data["password2"] = data["password1"]
        data["role"] = "ADMIN"
        data["is_staff"] = "true"
        response = self.client.post("/cuenta/registro/", data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.count(), 0)

    def test_external_next_is_rejected(self):
        data = self.data()
        data["password1"] = data.pop("password")
        data["password2"] = data["password1"]
        data["next"] = "https://example.org/steal"
        response = self.client.post("/cuenta/registro/", data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/mis-solicitudes/")

    def test_tax_id_rejects_unicode_digits_and_zero_padding(self):
        from accounts.identity import validate_rut

        for value in ["١٢٣٤٥٦٧٨-5", "01234567-4"]:
            with self.subTest(value=value), self.assertRaises(ValidationError):
                validate_rut(value)
