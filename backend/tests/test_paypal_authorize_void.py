from __future__ import annotations

import json
import unittest
from collections.abc import Iterator
from typing import Any

from paypal import PaypalClient
from paypal.core import ClientCredentials, HttpRequest, HttpResponse, JsonBody

from backend.paypal_authorize_void import create_authorize_and_void


class StubResponse:
    def __init__(self, url: str, status_code: int, body: dict[str, Any]) -> None:
        self.url = url
        self.status_code = status_code
        self.headers = {"content-type": "application/json"}
        self._content = json.dumps(body).encode()

    def iter_bytes(self, chunk_size: int | None) -> Iterator[bytes]:
        yield self._content

    def read(self) -> bytes:
        return self._content

    def close(self) -> None:
        return None


class StubTransport:
    def __init__(self, responses: list[tuple[int, dict[str, Any]]]) -> None:
        self._responses = responses
        self.requests: list[HttpRequest] = []

    def send(self, request: HttpRequest) -> HttpResponse:
        self.requests.append(request)
        status_code, body = self._responses.pop(0)
        return StubResponse(request.url, status_code, body)

    def close(self) -> None:
        return None


class PayPalAuthorizeVoidTests(unittest.TestCase):
    def test_creates_approved_order_authorizes_and_voids_it(self) -> None:
        approval_url = "https://www.sandbox.paypal.com/checkoutnow?token=ORDER-123"
        transport = StubTransport(
            [
                (200, {"access_token": "sandbox-token", "token_type": "Bearer", "expires_in": 3600}),
                (
                    201,
                    {
                        "id": "ORDER-123",
                        "intent": "AUTHORIZE",
                        "links": [{"href": approval_url, "rel": "approve", "method": "GET"}],
                    },
                ),
                (
                    200,
                    {
                        "id": "ORDER-123",
                        "intent": "AUTHORIZE",
                        "purchase_units": [
                            {"payments": {"authorizations": [{"id": "AUTH-123", "status": "CREATED"}]}}
                        ],
                    },
                ),
                (200, {"id": "AUTH-123", "status": "VOIDED"}),
            ]
        )
        client = PaypalClient(
            base_url="https://api-m.sandbox.paypal.com",
            retry_options=0,
            custom_http_client=transport,
            oauth2=ClientCredentials(client_id="client-id", client_secret="client-secret"),
        )
        approval_urls: list[str] = []

        def approve(url: str) -> None:
            self.assertEqual(len(transport.requests), 2)
            approval_urls.append(url)

        with client:
            result = create_authorize_and_void(
                client,
                return_url="http://localhost:3000/",
                approval_waiter=approve,
            )

        self.assertEqual(result.order_id, "ORDER-123")
        self.assertEqual(result.authorization_id, "AUTH-123")
        self.assertEqual(approval_urls, [approval_url])
        self.assertEqual(len(transport.requests), 4)
        self.assertEqual(
            [request.url.rsplit("api-m.sandbox.paypal.com", maxsplit=1)[-1] for request in transport.requests[1:]],
            [
                "/v2/checkout/orders",
                "/v2/checkout/orders/ORDER-123/authorize",
                "/v2/payments/authorizations/AUTH-123/void",
            ],
        )

        create_body = transport.requests[1].body
        self.assertIsInstance(create_body, JsonBody)
        assert isinstance(create_body, JsonBody)
        self.assertEqual(create_body.value["intent"], "AUTHORIZE")
        self.assertEqual(create_body.value["purchase_units"][0]["amount"], {"currency_code": "USD", "value": "10.00"})
        self.assertEqual(
            len({request.headers["paypal-request-id"] for request in transport.requests[1:]}),
            3,
        )


if __name__ == "__main__":
    unittest.main()