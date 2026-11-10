"""Servidor QA con base PostgreSQL temporal, separado de desarrollo."""

import os, sys, socket, secrets, json, threading, urllib.request
from pathlib import Path
from socketserver import ThreadingMixIn
from wsgiref.simple_server import WSGIServer, WSGIRequestHandler, make_server

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
PORT = 8014
if "--stop" in sys.argv:
    secret = (ROOT / ".local/ui_password").read_text()
    request = urllib.request.Request(
        f"http://127.0.0.1:{PORT}/_qa/stop/", data=b"", headers={"X-QA-Token": secret}
    )
    urllib.request.urlopen(request, timeout=10).close()
    raise SystemExit()
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "buildcorp.settings")
os.environ["DJANGO_DEBUG"] = "False"
os.environ["PUBLIC_BASE_URL"] = f"http://127.0.0.1:{PORT}"
import django

django.setup()
from django.test.utils import setup_databases, teardown_databases
from django.db import connection
from django.core.management import call_command
from django.core.wsgi import get_wsgi_application
from accounts.models import User
from inventory.models import Contractor

connection.settings_dict["TEST"]["NAME"] = "test_buildcorp_ui"
with socket.socket() as probe:
    probe.bind(("127.0.0.1", PORT))
old = setup_databases(verbosity=0, interactive=False)
try:
    call_command("seed_demo")
    password = secrets.token_urlsafe(24)
    (ROOT / ".local/ui_password").write_text(password)
    User.objects.create_superuser("QAManager", "manager@example.test", password)
    User.objects.create_user(
        "QAContractor",
        "contractor@example.test",
        password,
        contractor=Contractor.objects.first(),
    )
    app = get_wsgi_application()

    def qa(environ, start_response):
        if (
            environ.get("PATH_INFO") == "/_qa/stop/"
            and environ.get("REQUEST_METHOD") == "POST"
            and secrets.compare_digest(environ.get("HTTP_X_QA_TOKEN", ""), password)
        ):
            start_response("200 OK", [("Content-Type", "text/plain")])
            threading.Thread(target=server.shutdown, daemon=True).start()
            return [b"Closing QA"]
        return app(environ, start_response)

    class Server(ThreadingMixIn, WSGIServer):
        daemon_threads = True
        allow_reuse_address = False

    class QuietRequestHandler(WSGIRequestHandler):
        def log_message(self, format, *args):
            # No registrar parámetros de retorno ni tokens del proveedor en QA.
            pass

    with make_server(
        "127.0.0.1", PORT, qa, server_class=Server, handler_class=QuietRequestHandler
    ) as server:
        print("QA listo en http://127.0.0.1:8014/", flush=True)
        server.serve_forever()
finally:
    teardown_databases(old, verbosity=0)
    (ROOT / ".local/ui_password").unlink(missing_ok=True)
