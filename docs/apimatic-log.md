# APIMatic Context Plugin log

Evidence for the README's APIMatic section: what the plugin helped with, and what it saved us.

| Date | What I asked | What the plugin helped with | Evidence |
|------|--------------|-----------------------------|----------|
| 2026-10-10 | "Using the PayPal Server SDK for Python, show how to create an order with intent AUTHORIZE." | Generated a correct create-order request using the real SDK classes (`PaypalServersdkClient`, `OrderRequest`, `CheckoutPaymentIntent.AUTHORIZE`). Targets the sandbox, reads credentials from environment variables, and checks `is_success()`. Package name confirmed as `paypal-server-sdk`. | Output below; screenshot: `docs/screenshots/01-create-order.png` (add when captured) |
|      |      |      |      |

## Evidence 1: create order with AUTHORIZE intent (2026-10-10)

Plugin output, not yet run against the sandbox:

```python
import os

from paypalserversdk.configuration import Environment
from paypalserversdk.http.auth.o_auth_2 import ClientCredentialsAuthCredentials
from paypalserversdk.models.amount_with_breakdown import AmountWithBreakdown
from paypalserversdk.models.checkout_payment_intent import CheckoutPaymentIntent
from paypalserversdk.models.order_request import OrderRequest
from paypalserversdk.models.purchase_unit_request import PurchaseUnitRequest
from paypalserversdk.paypal_serversdk_client import PaypalServersdkClient

client = PaypalServersdkClient(
    client_credentials_auth_credentials=ClientCredentialsAuthCredentials(
        o_auth_client_id=os.environ["PAYPAL_CLIENT_ID"],
        o_auth_client_secret=os.environ["PAYPAL_CLIENT_SECRET"],
    ),
    environment=Environment.SANDBOX,
)

result = client.orders.create_order({
    "body": OrderRequest(
        intent=CheckoutPaymentIntent.AUTHORIZE,
        purchase_units=[
            PurchaseUnitRequest(
                amount=AmountWithBreakdown(
                    currency_code="USD",
                    value="10.00",
                )
            )
        ],
    ),
    "prefer": "return=representation",
})

if result.is_success():
    order = result.body
    print(order)
else:
    raise RuntimeError(f"PayPal create-order request failed: {result.errors}")
```

Still to do: run it against the sandbox and record whether it returned an order with status `CREATED`.

## Things the plugin got wrong or missed
- (fill in as we find them)

## What it saved us
- (rough time not spent reading docs)

## Evidence 2: skills change the answer (2026-10-10)
- Prompt: asked the agent to load python-getting-started, python-calling-endpoints and python-error-handling, then show an AUTHORIZE order with correct error handling.
- VS Code did not register the plugin's skills in the session (the agent said so), so it read the same skill files from GitHub and checked the SDK source.
- Result: it corrected the first example. The SDK raises on non-2xx responses, so the `is_success()` / `else` branch is wrong; catch `ErrorException`/`ApiException` and read `response_code`. It also added `paypal_request_id` for safe retries and separate handling for timeouts.
- Caveat: not yet run against the PayPal sandbox.

## Evidence 3: skill-specific details (2026-10-10)
- Prompt: how to check whether an optional response field was returned, and where to read the HTTP status on failure.
- Answer matched the skills: omitted optionals are absent (use `hasattr`, not `is None`); status code on `exc.response_code` for errors and `response.status_code` for successes.
- Caveat: the agent also had access to the SDK source, so this shows consistency with the skills, not proof they were the source. On/off comparison not yet run.
