import pytest
from paypalserversdk.exceptions.api_exception import ApiException

from app.config import settings
from app.services.paypal import build_client

pytestmark = pytest.mark.skipif(
    not (settings.paypal_client_id and settings.paypal_client_secret),
    reason="PayPal sandbox credentials are not configured",
)


def status_of_authenticated_call(client) -> int:
    """Make a harmless authenticated read. A made-up order ID is expected to
    fail with 'not found', which still proves the login was accepted."""
    try:
        return client.orders.get_order({"id": "0000000000000000"}).status_code
    except ApiException as exc:
        return exc.response_code


def test_token_is_fetched_once_reused_then_renewed_after_expiry():
    fetched = []
    client = build_client(on_token_update=fetched.append)

    assert status_of_authenticated_call(client) != 401
    assert len(fetched) == 1, "first call should fetch one token"

    assert status_of_authenticated_call(client) != 401
    assert len(fetched) == 1, "second call should reuse the cached token"

    fetched[0].expiry = 0  # pretend the token ran out long ago

    assert status_of_authenticated_call(client) != 401
    assert len(fetched) == 2, "an expired token should be replaced automatically"