# PayPal Python Order Authorize and Void Plan

## Goal

Add a small synchronous Python example under `backend/` that creates one sandbox PayPal order with `AUTHORIZE` intent, opens the buyer approval link, waits for the buyer to approve, authorizes the order, and voids the resulting authorization. It does not capture funds.

## Repository Survey

- Horkos has no Python backend application yet; `backend/` contains only `.gitkeep`. The integration will therefore be a standalone synchronous CLI module, not a FastAPI route.
- Repository PayPal environment variable names are already established in `.env.example`: `PAYPAL_CLIENT_ID`, `PAYPAL_CLIENT_SECRET`, and `PAYPAL_ENVIRONMENT=sandbox`. Credentials are not set in the current process, and no `.env` is loaded by the shell.
- Horkos has no Python dependency manifest, test suite, or type-checker configuration. Python 3.14.8 is available. The repository ignores `.venv/`.
- The PayPal integration workflow's `python-getting-started` snapshot identifies an older import/package surface. The checked-out SDK `main` branch map and installed source resolve this drift: current package/distribution is `paypal==2.29`, import root `paypal`, with `PaypalClient`. Use the installed package and checked-out map as the contract source.
- SDK source revision: `1b72465878f0187f88ef326214e08859d3ab0851`; installed in the ignored Horkos `.venv` from the SDK repository. The dependency will pin this commit.
- No real API smoke test can run because sandbox credentials are absent. This is an environment limitation, not an open SDK contract lookup. Baseline Python tests/type checks do not exist; baseline is therefore not applicable.

## Decisions

- Use the sync client because this is a standalone script, not an async web handler.
- Use the buyer-approval flow because `authorize_order` requires buyer approval or a valid payment source. No payment source was provided. Create exactly one purchase unit, show/open the approval URL, and wait for explicit confirmation before authorizing.
- Use the explicit sandbox host `https://api-m.sandbox.paypal.com`, a 15-second timeout, managed OAuth client credentials, and `retry_options=0` to avoid automatic retries of financial writes. No credentials are embedded in source.
- Use one USD sample amount (`10.00`) and the current `payment_source.paypal.experience_context` return/cancel URL fields. A return URL defaults to the existing local frontend origin and may be overridden with `PAYPAL_RETURN_URL`.
- Treat API errors, OAuth errors, transport errors, and unreadable response bodies distinctly. Never retry a write automatically after an ambiguous transport/decode failure.

## Contract Sheet

SDK lookup sources: cloned SDK `sdk-map.md`, `map/operations/orders.md`, `map/operations/payments.md`, `api-reference.md`, and the corresponding modules in the installed `paypal` package.

### Client and Auth

- Client: `paypal.PaypalClient`, constructed with keyword-only options. Verified in `paypal/client.py` and `sdk-map.md`.
- Auth: `oauth2=ClientCredentials(client_id: str, client_secret: str, scopes: list[str] | None)`. The SDK fetches/caches the OAuth token lazily. Verified in `paypal/core` and `paypal/client.py`.
- Server: one base URL; default is sandbox, but code will pass `base_url="https://api-m.sandbox.paypal.com"` explicitly. Timeout is seconds; set to `15.0`.
- Client lifetime: context manager closes its HTTP pool. The SDK accepts `retry_options=0` to disable retries.
- SDK error/runtime imports: `ApiError`, `OAuthProviderError`, `RawError`, `ClientCredentials` from `paypal.core`; `Error` from `paypal.models`; transport exceptions from `httpx2` (the installed SDK transport dependency).

### `client.orders.create_order`

- Method/route: `POST /v2/checkout/orders`.
- Sync signature: `create_order(body: OrderRequest | OrderRequestDict, *, ..., prefer: str | None = "return=minimal", ..., request_options=None) -> Order`.
- Required positional argument is the request body. `pay_pal_request_id` is optional and keyword-only; `prefer` defaults to the minimal representation. Use `prefer="return=representation"` and a unique request ID.
- Error union: `CreateOrderErrorBody = Error | RawError`; `Error` maps 400/401/422, `RawError` handles other/unmapped statuses.
- `OrderRequest`: required `intent: CheckoutPaymentIntentOrStr` and `purchase_units: list[PurchaseUnitRequest]`; optional `payment_source` and other fields. Fields confirmed in `paypal/models/order_request.py`.
- `CheckoutPaymentIntent.AUTHORIZE` has wire value `AUTHORIZE`. Its SDK doc says this intent is not supported with multiple purchase units. Use one purchase unit.
- `PurchaseUnitRequest.amount` is required `AmountWithBreakdown`; `currency_code` and `value` are required strings. The amount must be positive. Use `USD` / `10.00`. Confirmed in `paypal/models/purchase_unit_request.py` and `amount_with_breakdown.py`.
- For current PayPal checkout context, set `payment_source.paypal.experience_context.return_url` and `cancel_url`; members confirmed in `payment_source.py`, `pay_pal_wallet.py`, and `pay_pal_wallet_experience_context.py`. The older `application_context` model is deprecated.
- `Order.id` and `Order.links` are optional (`str | UnsetType`, `list[LinkDescription] | UnsetType`). `LinkDescription.href` and `.rel` are required. Require an order ID and the `approve` link before continuing. Confirmed in `order.py` and `link_description.py`.

### `client.orders.authorize_order`

- Method/route: `POST /v2/checkout/orders/{id}/authorize`.
- Sync signature: `authorize_order(id_: str, *, ..., prefer: str | None = "return=minimal", ..., body: OrderAuthorizeRequest | OrderAuthorizeRequestDict | None = None, request_options=None) -> OrderAuthorizeResponse`.
- `id_` is required positional; remaining arguments are keyword-only and optional. Use `prefer="return=representation"` and a unique request ID.
- Error union: `AuthorizeOrderErrorBody = Error | RawError`; `Error` maps 400/401/403/404/422/500, `RawError` handles other/unmapped statuses.
- Behavioral precondition from the operation docstring: buyer must approve the order first, or a valid `payment_source` must be provided. This example uses the buyer approval URL returned by create order and pauses until the buyer returns.
- Response lookup for authorization ID: `OrderAuthorizeResponse.purchase_units` (optional list) → `PurchaseUnit.payments` (optional `PaymentCollection`) → `PaymentCollection.authorizations` (optional list of `AuthorizationWithAdditionalData`) → `.id` (optional string). Validate every optional response member before use.

### `client.payments.void_payment`

- Method/route: `POST /v2/payments/authorizations/{authorization_id}/void`.
- Sync signature: `void_payment(authorization_id: str, *, ..., pay_pal_request_id: str | None = None, prefer: str | None = "return=minimal", request_options=None) -> PaymentAuthorization`.
- `authorization_id` is required positional; all other parameters are keyword-only and optional. Use `prefer="return=representation"` and a unique request ID.
- Error union: `VoidPaymentErrorBody = Error | RawError`; `Error` maps 401/403/404/409/422, `RawError` handles 500 and other/unmapped statuses.
- `PaymentAuthorization.id` and `.status` are optional response fields. `AuthorizationStatus.VOIDED` is the wire value `VOIDED`; check the returned status. Confirmed in `payment_authorization.py` and `enums/authorization_status.py`.
- The operation docstring says void cancels an authorized payment and cannot void one that is fully captured.

### Error and Model Rules

- `ApiError.error` is the per-operation union above. OAuth token failures also surface as `ApiError` carrying `OAuthProviderError | RawError`; distinguish that before operation errors. Typed API errors expose `.message`; raw bodies expose `.text()`.
- Response decode failures raise `ValueError`/Pydantic `ValidationError`, not `ApiError`; transport failures surface as the HTTP library exception (`httpx2.HTTPError` for the installed SDK transport). A failed write's outcome can be unknown; report that and do not retry blindly.
- SDK models are frozen. SDK `Optional[T]` fields are `T | UnsetType`, not `typing.Optional`; validate optional response members with type checks before using them. Models serialize using PayPal wire names.

## Implementation and Verification

1. Add `backend/requirements.txt` pinned to SDK source revision `1b72465878f0187f88ef326214e08859d3ab0851`.
2. Add a CLI module that implements the approval → authorize → void sequence and reads secrets from environment variables.
3. Add focused `unittest` coverage using the SDK transport protocol with queued token/order/authorization/void responses; assert the request order, `AUTHORIZE` wire intent, authorization ID path, and final `VOIDED` status without network access.
4. Run `python -m unittest discover -s backend/tests`, `mypy --strict` on the touched Python files, and `python -m compileall` on the backend module. A real sandbox call remains unverified until credentials are supplied.

## REQUIRED READING

- `python-client-initialization` — MUST load (loaded): sync client lifetime and cleanup.
- `python-authentication` — MUST load (loaded): managed OAuth and secret handling.
- `python-calling-endpoints` — MUST load (loaded): positional/keyword-only operation calls and response access.
- `python-models` — MUST load (loaded): request/response model shapes and `UNSET` semantics.
- `python-error-handling` — MUST load (loaded): typed API, auth, decode, and transport failures.
- `python-configuration-resilience` — MUST load (loaded): explicit sandbox URL, timeout, and write retry choice.
- `python-testing` — MUST load (loaded): transport-level tests.

Open SDK contract lookups: none. Live API behavior remains unverified because credentials are not configured.
