"""Create, authorize, and void one PayPal sandbox order.

Set PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET before running this script. The
buyer must approve the order in the browser before the authorization step.
"""

from __future__ import annotations

import os
import sys
import webbrowser
from collections.abc import Callable
from dataclasses import dataclass
from uuid import uuid4

import httpx2
from paypal import PaypalClient
from paypal.core import ApiError, ClientCredentials, OAuthProviderError, RawError, UnsetType
from paypal.models import (
    AmountWithBreakdown,
    Error,
    OrderRequest,
    PayPalWallet,
    PayPalWalletExperienceContext,
    PaymentSource,
    PurchaseUnitRequest,
)
from paypal.models.enums import AuthorizationStatus, CheckoutPaymentIntent

PAYPAL_SANDBOX_URL = "https://api-m.sandbox.paypal.com"
DEFAULT_RETURN_URL = "http://localhost:3000/"


class PayPalFlowError(RuntimeError):
    """A PayPal operation failed or returned data the flow cannot safely use."""


@dataclass(frozen=True)
class OrderFlowResult:
    order_id: str
    authorization_id: str


def _wait_for_buyer_approval(approval_url: str) -> None:
    print(f"Approve this order in PayPal: {approval_url}")
    webbrowser.open(approval_url)
    input("After approving the order in your browser, press Enter to continue: ")


def create_authorize_and_void(
    client: PaypalClient,
    *,
    return_url: str,
    approval_waiter: Callable[[str], None] = _wait_for_buyer_approval,
) -> OrderFlowResult:
    request = OrderRequest(
        intent=CheckoutPaymentIntent.AUTHORIZE,
        purchase_units=[
            PurchaseUnitRequest(amount=AmountWithBreakdown(currency_code="USD", value="10.00")),
        ],
        payment_source=PaymentSource(
            paypal=PayPalWallet(
                experience_context=PayPalWalletExperienceContext(
                    return_url=return_url,
                    cancel_url=return_url,
                ),
            ),
        ),
    )

    try:
        order = client.orders.create_order(
            request,
            pay_pal_request_id=str(uuid4()),
            prefer="return=representation",
        )
        if not isinstance(order.id, str) or not order.id:
            raise PayPalFlowError("PayPal created an order without returning its ID; check the sandbox order state.")

        if not isinstance(order.links, list):
            raise PayPalFlowError("PayPal created an order without returning approval links.")
        approval_url = next((link.href for link in order.links if link.rel == "approve"), None)
        if approval_url is None:
            raise PayPalFlowError("PayPal did not return an approval link for the new order.")

        approval_waiter(approval_url)

        authorized_order = client.orders.authorize_order(
            order.id,
            pay_pal_request_id=str(uuid4()),
            prefer="return=representation",
        )
        purchase_units = authorized_order.purchase_units
        if not isinstance(purchase_units, list) or not purchase_units:
            raise PayPalFlowError("PayPal authorization response did not include a purchase unit.")

        payments = purchase_units[0].payments
        if isinstance(payments, UnsetType):
            raise PayPalFlowError("PayPal authorization response did not include payment details.")
        authorizations = payments.authorizations
        if not isinstance(authorizations, list) or not authorizations:
            raise PayPalFlowError("PayPal authorization response did not include an authorization.")
        authorization_id = authorizations[0].id
        if not isinstance(authorization_id, str) or not authorization_id:
            raise PayPalFlowError("PayPal authorization response did not include an authorization ID.")

        voided = client.payments.void_payment(
            authorization_id,
            pay_pal_request_id=str(uuid4()),
            prefer="return=representation",
        )
        if voided.status != AuthorizationStatus.VOIDED:
            raise PayPalFlowError(f"PayPal returned unexpected authorization status: {voided.status!r}.")

        return OrderFlowResult(order_id=order.id, authorization_id=authorization_id)
    except ApiError as error:
        if isinstance(error.error, OAuthProviderError):
            detail = error.error.error_description or error.error.error
        elif isinstance(error.error, Error):
            detail = error.error.message
        elif isinstance(error.error, RawError):
            detail = error.error.text()
        else:
            detail = "unrecognized error response"
        raise PayPalFlowError(f"PayPal returned HTTP {error.status_code}: {detail}") from error
    except httpx2.HTTPError as error:
        raise PayPalFlowError(
            "PayPal could not be reached; the last write may have succeeded. Check the sandbox order before retrying."
        ) from error
    except ValueError as error:
        raise PayPalFlowError(
            "PayPal returned an unreadable response; the last write may have succeeded. "
            "Check the sandbox order before retrying."
        ) from error


def main() -> None:
    client_id = os.getenv("PAYPAL_CLIENT_ID")
    client_secret = os.getenv("PAYPAL_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise SystemExit("Set PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET to sandbox credentials.")

    return_url = os.getenv("PAYPAL_RETURN_URL", DEFAULT_RETURN_URL)
    try:
        with PaypalClient(
            base_url=PAYPAL_SANDBOX_URL,
            timeout=15.0,
            retry_options=0,
            oauth2=ClientCredentials(client_id=client_id, client_secret=client_secret),
        ) as client:
            result = create_authorize_and_void(client, return_url=return_url)
    except PayPalFlowError as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1) from error

    print(f"Order {result.order_id} authorized and voided (authorization {result.authorization_id}).")


if __name__ == "__main__":
    main()