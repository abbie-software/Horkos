import secrets
import time
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import httpx
from paypalserversdk.exceptions.api_exception import ApiException
from paypalserversdk.models.amount_with_breakdown import AmountWithBreakdown
from paypalserversdk.models.checkout_payment_intent import CheckoutPaymentIntent
from paypalserversdk.models.order_application_context import OrderApplicationContext
from paypalserversdk.models.order_request import OrderRequest
from paypalserversdk.models.purchase_unit_request import PurchaseUnitRequest

from app.config import settings
from app.services.funding import FundingError, FundingStart, NotApprovedYet
from app.services.paypal import get_client

BASE_URL = "https://api-m.sandbox.paypal.com"
PAYOUT_POLL_SECONDS = 3
PAYOUT_POLL_TRIES = 5
FAILED_PAYOUT_STATES = {"FAILED", "DENIED", "BLOCKED", "RETURNED", "REVERSED", "REFUNDED"}


def money(cents: int) -> str:
    """Whole cents to PayPal's amount text, with integer math only: 2000 -> 20.00."""
    return f"{cents // 100}.{cents % 100:02d}"


def with_query(url: str, **params: str) -> str:
    parts = urlparse(url)
    query = dict(parse_qsl(parts.query))
    query.update(params)
    return urlunparse(parts._replace(query=urlencode(query)))


def plain(value):
    """PayPal's SDK returns some fields as enums. This gives their text."""
    return getattr(value, "value", value)


class PayPalFunder:
    """Moves real money in the PayPal sandbox.

    hold:   an order with intent AUTHORIZE, which the buyer approves on PayPal.
    pass:   capture the hold, then pay the seller with PayPal Payouts.
    fail:   void the hold, or refund it if it was already captured.
    """

    def __init__(self, client=None, http=None, sleep=time.sleep):
        self._client = client
        self._http = http
        self._sleep = sleep

    def _sdk(self):
        if self._client is not None:
            return self._client
        try:
            return get_client()
        except RuntimeError as exc:
            raise FundingError(str(exc)) from exc

    def start(self, payment, seller) -> FundingStart:
        client = self._sdk()
        label = f"pay_{payment.id}"
        try:
            response = client.orders.create_order(
                {
                    "body": OrderRequest(
                        intent=CheckoutPaymentIntent.AUTHORIZE,
                        purchase_units=[
                            PurchaseUnitRequest(
                                amount=AmountWithBreakdown(
                                    currency_code="USD",
                                    value=money(payment.amount_cents),
                                )
                            )
                        ],
                        application_context=OrderApplicationContext(
                            return_url=with_query(settings.paypal_return_url, payment=label),
                            cancel_url=with_query(
                                settings.paypal_cancel_url, payment=label, cancelled="1"
                            ),
                        ),
                    ),
                    "prefer": "return=representation",
                }
            )
        except ApiException as exc:
            raise FundingError(
                f"PayPal could not create the order (HTTP {exc.response_code})."
            ) from exc

        order = response.body
        order_id = getattr(order, "id", None)
        approve_url = next(
            (
                link.href
                for link in (getattr(order, "links", None) or [])
                if link.rel == "approve"
            ),
            None,
        )
        if not order_id or not approve_url:
            raise FundingError("PayPal did not return an approval link.")
        return FundingStart(ref=order_id, held=False, approve_url=approve_url)

    def confirm(self, payment) -> str:
        client = self._sdk()
        try:
            response = client.orders.authorize_order(
                {"id": payment.paypal_order_id, "prefer": "return=representation"}
            )
        except ApiException as exc:
            body = str(getattr(exc, "body", "") or "")
            if exc.response_code == 422 and (not body or "ORDER_NOT_APPROVED" in body):
                raise NotApprovedYet(
                    "The buyer has not approved this payment on PayPal yet."
                ) from exc
            raise FundingError(
                f"PayPal could not place the hold (HTTP {exc.response_code})."
            ) from exc

        authorizations = [
            authorization
            for unit in (getattr(response.body, "purchase_units", None) or [])
            for authorization in (
                getattr(getattr(unit, "payments", None), "authorizations", None) or []
            )
        ]
        if len(authorizations) != 1 or not getattr(authorizations[0], "id", None):
            raise FundingError("PayPal did not return exactly one authorization.")
        return authorizations[0].id

    def capture(self, payment) -> str:
        client = self._sdk()
        try:
            response = client.payments.capture_authorized_payment(
                {
                    "authorization_id": payment.paypal_authorization_id,
                    "prefer": "return=representation",
                }
            )
        except ApiException as exc:
            raise FundingError(
                f"PayPal could not capture the hold (HTTP {exc.response_code})."
            ) from exc
        status = plain(getattr(response.body, "status", None))
        capture_id = getattr(response.body, "id", None)
        if status != "COMPLETED" or not capture_id:
            raise FundingError(f"PayPal did not complete the capture (status {status}).")
        return capture_id

    def refund(self, payment) -> str:
        client = self._sdk()
        try:
            if payment.paypal_capture_id:
                response = client.payments.refund_captured_payment(
                    {
                        "capture_id": payment.paypal_capture_id,
                        "prefer": "return=representation",
                    }
                )
                return f"REFUNDED-{getattr(response.body, 'id', payment.paypal_capture_id)}"
            client.payments.void_payment(
                {
                    "authorization_id": payment.paypal_authorization_id,
                    "prefer": "return=representation",
                }
            )
            return f"VOIDED-{payment.paypal_authorization_id}"
        except ApiException as exc:
            raise FundingError(
                f"PayPal could not give the money back (HTTP {exc.response_code})."
            ) from exc

    def payout(self, payment, seller) -> str:
        http = self._http or httpx.Client(timeout=30)
        try:
            return self._payout(http, payment, seller)
        except httpx.HTTPError as exc:
            raise FundingError("Could not reach PayPal to pay the seller.") from exc
        finally:
            if self._http is None:
                http.close()

    def _payout(self, http, payment, seller) -> str:
        token = http.post(
            f"{BASE_URL}/v1/oauth2/token",
            auth=(settings.paypal_client_id, settings.paypal_client_secret),
            data={"grant_type": "client_credentials"},
        )
        if token.status_code >= 300:
            raise FundingError(f"PayPal login failed (HTTP {token.status_code}).")
        headers = {"Authorization": f"Bearer {token.json()['access_token']}"}

        # In the demo every seller can be paid into one sandbox account.
        receiver = settings.paypal_payout_email or seller.paypal_email
        created = http.post(
            f"{BASE_URL}/v1/payments/payouts",
            headers=headers,
            json={
                "sender_batch_header": {
                    # PayPal wants a new ID every time, so a demo reset cannot clash.
                    "sender_batch_id": f"horkos-{payment.id}-{secrets.token_hex(4)}",
                    "email_subject": "You were paid through Horkos",
                },
                "items": [
                    {
                        "recipient_type": "EMAIL",
                        "amount": {"value": money(payment.amount_cents), "currency": "USD"},
                        "receiver": receiver,
                        "note": f"Horkos payment pay_{payment.id}",
                        "sender_item_id": f"pay_{payment.id}",
                    }
                ],
            },
        )
        if created.status_code >= 300:
            detail = created.json() if created.content else {}
            raise FundingError(
                "PayPal refused the payout: "
                f"{detail.get('name', created.status_code)} {detail.get('message', '')}".strip()
            )
        batch_id = created.json()["batch_header"]["payout_batch_id"]

        for _ in range(PAYOUT_POLL_TRIES):
            self._sleep(PAYOUT_POLL_SECONDS)
            details = http.get(f"{BASE_URL}/v1/payments/payouts/{batch_id}", headers=headers)
            if details.status_code >= 300:
                continue
            data = details.json()
            states = [item.get("transaction_status") for item in data.get("items", [])]
            if any(state in FAILED_PAYOUT_STATES for state in states):
                raise FundingError(f"PayPal could not complete the payout ({', '.join(states)}).")
            if data["batch_header"]["batch_status"] == "SUCCESS":
                break
        return batch_id
