from django.test import Client
from accounts.permissions import can_operate
from tests.base import DomainCase


class AccountTests(DomainCase):
    def test_staff_does_not_grant_business_role(self):
        self.customer.is_staff = True
        self.customer.save()
        self.assertFalse(can_operate(self.customer))

    def test_contractor_cannot_manage_users(self):
        self.client.force_login(self.customer)
        self.assertEqual(self.client.get("/admin/accounts/user/").status_code, 302)

    def test_login_logout(self):
        self.assertTrue(
            self.client.login(username="cliente", password="ClaveLocalSegura.123")
        )
        self.client.logout()
        self.assertNotIn("_auth_user_id", self.client.session)
