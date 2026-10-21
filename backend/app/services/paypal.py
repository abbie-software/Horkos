from paypalserversdk.configuration import Environment
from paypalserversdk.http.auth.o_auth_2 import ClientCredentialsAuthCredentials
from paypalserversdk.paypal_serversdk_client import PaypalServersdkClient

from app.config import settings

_client: PaypalServersdkClient | None = None


def build_client(on_token_update=None, clock_skew=None) -> PaypalServersdkClient:
    if settings.paypal_environment != "sandbox":
        raise RuntimeError("Horkos only runs against the PayPal sandbox.")
    if not settings.paypal_client_id or not settings.paypal_client_secret:
        raise RuntimeError("PayPal credentials are missing from .env.")

    return PaypalServersdkClient(
        client_credentials_auth_credentials=ClientCredentialsAuthCredentials(
            o_auth_client_id=settings.paypal_client_id,
            o_auth_client_secret=settings.paypal_client_secret,
            o_auth_on_token_update=on_token_update,
            o_auth_clock_skew=clock_skew,
        ),
        environment=Environment.SANDBOX,
    )


def get_client() -> PaypalServersdkClient:
    """Return the one shared client. The SDK refreshes its token when needed."""
    global _client
    if _client is None:
        _client = build_client()
    return _client