from django.test import TestCase

from accounts.models import User


class CustomAdministrationTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user("gestion", role=User.Role.ADMIN)
        self.store = User.objects.create_user(
            "bodega", role=User.Role.STORE, is_staff=True
        )
        self.root = User.objects.create_superuser("root")
        self.customer = User.objects.create_user("cliente")

    def test_custom_panel_requires_active_admin(self):
        self.assertRedirects(
            self.client.get("/admin/"),
            "/accounts/login/?next=/admin/",
            fetch_redirect_response=False,
        )
        for user in (self.store, self.customer):
            self.client.force_login(user)
            self.assertEqual(self.client.get("/admin/").status_code, 403)
            self.assertEqual(
                self.client.post("/admin/usuarios/nuevo/").status_code, 403
            )
        self.client.force_login(self.admin)
        self.assertTemplateUsed(self.client.get("/admin/"), "administration/index.html")
        self.assertContains(self.client.get("/admin/usuarios/?q=bodega"), "bodega")
        self.assertEqual(self.client.get("/admin/accounts/user/").status_code, 404)

    def test_create_staff_hashes_password_and_does_not_grant_superuser(self):
        self.client.force_login(self.admin)
        password = "UnaClaveInterna.678"
        response = self.client.post(
            "/admin/usuarios/nuevo/",
            {
                "username": "operador",
                "role": User.Role.STORE,
                "password1": password,
                "password2": password,
                "is_superuser": "on",
            },
        )
        self.assertRedirects(response, "/admin/usuarios/")
        account = User.objects.get(username="operador")
        self.assertTrue(account.check_password(password))
        self.assertFalse(account.is_superuser)
        self.assertEqual(account.role, User.Role.STORE)

    def test_edit_changes_role_and_status_for_staff(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            f"/admin/usuarios/{self.store.pk}/editar/",
            {"role": User.Role.ADMIN},
        )
        self.assertRedirects(response, "/admin/usuarios/")
        self.store.refresh_from_db()
        self.assertEqual(self.store.role, User.Role.ADMIN)
        self.assertFalse(self.store.is_active)

    def test_protected_accounts_and_customer_role(self):
        self.client.force_login(self.admin)
        for account in (self.admin, self.root):
            self.assertEqual(
                self.client.post(f"/admin/usuarios/{account.pk}/editar/").status_code,
                403,
            )
        response = self.client.post(
            f"/admin/usuarios/{self.customer.pk}/editar/",
            {"role": User.Role.ADMIN, "is_active": "on"},
        )
        self.assertRedirects(response, "/admin/usuarios/")
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.role, User.Role.CONTRACTOR)
