"""Cliente REST Webpay Plus. Solo integración; credenciales públicas oficiales."""

import json, re
from urllib.request import Request, urlopen
from urllib.parse import urlsplit
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

BASE = (
    "https://webpay3gint.transbank.cl/rswebpaytransaction/api/webpay/v1.2/transactions"
)


class WebpayGateway:
    def _request(self, method, token="", data=None):
        if settings.WEBPAY_ENV != "integration":
            raise ImproperlyConfigured("Webpay solo admite integración.")
        if token and not re.fullmatch(r"[A-Za-z0-9_-]{1,200}", token):
            raise ValueError("Token inválido")
        request = Request(
            BASE + ("/" + token if token else ""),
            data=json.dumps(data).encode() if data is not None else None,
            method=method,
            headers={
                "Content-Type": "application/json",
                "Tbk-Api-Key-Id": "597055555532",
                "Tbk-Api-Key-Secret": "579B532A7440BB0C9079DED94D31EA1615BACEB56610332264630D42D0A36B1C",
            },
        )
        with urlopen(request, timeout=15) as response:
            if urlsplit(response.url).hostname != "webpay3gint.transbank.cl":
                raise ValueError("Host inesperado")
            return json.loads(response.read(100000).decode())

    def create(self, *, buy_order, session_id, amount, return_url):
        return self._request(
            "POST",
            data=dict(
                buy_order=buy_order,
                session_id=session_id,
                amount=amount,
                return_url=return_url,
            ),
        )

    def commit(self, token):
        return self._request("PUT", token, data={})

    def status(self, token):
        return self._request("GET", token)
