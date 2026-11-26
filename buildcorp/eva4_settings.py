from datetime import timedelta

from .settings import *

EVA4_INTERNAL = True
ROOT_URLCONF = "buildcorp.eva4_urls"
REST_FRAMEWORK = {
    **REST_FRAMEWORK,
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": ["accounts.permissions.OperatorPermission"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
}
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=5),
    "REFRESH_TOKEN_LIFETIME": timedelta(hours=8),
    "SIGNING_KEY": env("JWT_SIGNING_KEY", default=SECRET_KEY if DEBUG else ""),
}
if len(SIMPLE_JWT["SIGNING_KEY"]) < 32:
    raise ImproperlyConfigured("Configura JWT_SIGNING_KEY (mínimo 32 caracteres).")
if env.bool("DB_TLS", default=False):
    DATABASES["default"]["OPTIONS"].update(
        sslmode="verify-full", sslrootcert=env("DB_SSL_ROOT_CERT")
    )
