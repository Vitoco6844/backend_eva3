import unittest
from importlib.util import find_spec


class ArchitectureTests(unittest.TestCase):
    def test_required_domain_modules_exist(self):
        for app in (
            "accounts",
            "inventory",
            "rentals",
            "maintenance",
            "payments",
            "web",
        ):
            with self.subTest(app=app):
                self.assertIsNotNone(find_spec(app), f"Falta módulo {app}")
