import os, subprocess, sys
from django.test import SimpleTestCase


class SettingsTests(SimpleTestCase):
    def test_production_config_rejected(self):
        env = os.environ.copy()
        env["WEBPAY_ENV"] = "production"
        result = subprocess.run(
            [sys.executable, "-c", "import buildcorp.settings"],
            env=env,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Solo se permite Webpay", result.stderr)
