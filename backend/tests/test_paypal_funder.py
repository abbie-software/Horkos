from types import SimpleNamespace

from paypalserversdk.exceptions.api_exception import ApiException
from paypalserversdk.models.checkout_payment_intent import CheckoutPaymentIntent

from app.config import settings
from app.services.funding import FundingError, NotApprovedYet
from app.services.paypal_funder import PayPalFunder, money, with_query

PAYMENT = SimpleNamespace(
    id=7,
    amount_cents=2000,
    paypal_order_id="ORDER-1",
    paypal_authorization_id="AUTH-1",
    paypal_capture_id=None,
)
SELLER = SimpleNamespace(paypal_email="nova-seller@example.com")


class FakeApiError(ApiException):
    def __init__(self, code, body=""):
        Exception.__init__(self, "PayPal said no")
        self.reason, self.response_code, self.body = "PayPal said no", code, body


class Settings:
    """Sets a few settings for one block, then puts them back."""

    def __init__(self, **values):
        self.values = values

    def __enter__(self):
        self.before = {name: getattr(settings, name) for name in self.values}
        for name, value in self.values.items():
            setattr(settings, name, value)

    def __exit__(self, *args):
        for name, value in self.before.items():
            setattr(settings, name, value)


class FakeSdk:
    def __init__(self):
        self.calls = []
        self.errors = {}
        self.capture_status = "COMPLETED"
        self.orders = SimpleNamespace(
            create_order=lambda request: self._call("create_order", request),
            authorize_order=lambda request: self._call("authorize_order", request),
        )
        self.payments = SimpleNamespace(
            capture_authorized_payment=lambda request: self._call("capture", request),
            void_payment=lambda request: self._call("void", request),
            refund_captured_payment=lambda request: self._call("refund", request),
        )

    def _call(self, name, request):
        self.calls.append((name, request))
        if name in self.errors:
            raise self.errors[name]
        if name == "create_order":
            links = [
                SimpleNamespace(rel="self", href="https://api.sandbox.paypal.com/x"),
                SimpleNamespace(rel="approve", href="https://www.sandbox.paypal.com/checkoutnow?token=ORDER-1"),
            ]
            return SimpleNamespace(body=SimpleNamespace(id="ORDER-1", links=links))
        if name == "authorize_order":
            auth = SimpleNamespace(id="AUTH-1")
            unit = SimpleNamespace(payments=SimpleNamespace(authorizations=[auth]))
            return SimpleNamespace(body=SimpleNamespace(purchase_units=[unit]))
        if name == "capture":
            return SimpleNamespace(body=SimpleNamespace(id="CAP-1", status=self.capture_status))
        return SimpleNamespace(body=SimpleNamespace(id="REF-1"))


class FakeResponse:
    def __init__(self, status_code=200, data=None):
        self.status_code, self._data = status_code, data

    @property
    def content(self):
        return b"{}" if self._data is not None else b""

    def json(self):
        return self._data


class FakeHttp:
    def __init__(self, polls=(("SUCCESS", "SUCCESS"),), create_status=201, create_body=None):
        self.calls, self.polls, self.poll_index = [], list(polls), 0
        self.create_status = create_status
        self.create_body = create_body or {
            "batch_header": {"payout_batch_id": "BATCH-1", "batch_status": "PENDING"}
        }

    def post(self, url, **kwargs):
        self.calls.append(("post", url, kwargs))
        if "oauth2/token" in url:
            return FakeResponse(200, {"access_token": "TOKEN"})
        return FakeResponse(self.create_status, self.create_body)

    def get(self, url, **kwargs):
        self.calls.append(("get", url, kwargs))
        batch, item = self.polls[min(self.poll_index, len(self.polls) - 1)]
        self.poll_index += 1
        return FakeResponse(
            200,
            {"batch_header": {"batch_status": batch}, "items": [{"transaction_status": item}]},
        )


def funder(sdk=None, http=None):
    slept = []
    instance = PayPalFunder(client=sdk, http=http, sleep=slept.append)
    instance.slept = slept
    return instance


def raised(call, kind):
    try:
        call()
    except kind as exc:
        return exc
    raise AssertionError(f"expected {kind.__name__}")


def test_money_is_written_the_way_paypal_wants_it():
    assert money(2000) == "20.00"
    assert money(5) == "0.05"
    assert money(100000) == "1000.00"
    assert money(2550) == "25.50"


def test_return_links_keep_their_own_query_and_add_the_payment():
    assert with_query("http://x/y", payment="pay_7") == "http://x/y?payment=pay_7"
    assert with_query("http://x/y?a=1", payment="pay_7") == "http://x/y?a=1&payment=pay_7"


def test_starting_creates_an_authorize_order_and_returns_the_approval_link():
    sdk = FakeSdk()
    with Settings(paypal_return_url="http://localhost:3000/money-tracker"):
        start = funder(sdk).start(PAYMENT, SELLER)
    assert start.held is False
    assert start.ref == "ORDER-1"
    assert start.approve_url.endswith("token=ORDER-1")

    name, request = sdk.calls[0]
    body = request["body"]
    assert name == "create_order"
    assert body.intent == CheckoutPaymentIntent.AUTHORIZE
    assert body.purchase_units[0].amount.value == "20.00"
    assert body.purchase_units[0].amount.currency_code == "USD"
    assert body.application_context.return_url.endswith("?payment=pay_7")
    assert "cancelled=1" in body.application_context.cancel_url


def test_starting_fails_cleanly_when_paypal_does_not_cooperate():
    broken = FakeSdk()
    broken.errors["create_order"] = FakeApiError(500)
    assert "HTTP 500" in str(raised(lambda: funder(broken).start(PAYMENT, SELLER), FundingError))

    no_link = FakeSdk()
    no_link.orders = SimpleNamespace(
        create_order=lambda request: SimpleNamespace(
            body=SimpleNamespace(id="ORDER-1", links=[])
        )
    )
    raised(lambda: funder(no_link).start(PAYMENT, SELLER), FundingError)


def test_confirming_returns_the_authorization():
    sdk = FakeSdk()
    assert funder(sdk).confirm(PAYMENT) == "AUTH-1"
    name, request = sdk.calls[0]
    assert (name, request["id"]) == ("authorize_order", "ORDER-1")


def test_confirming_before_the_buyer_approves_is_not_approved_yet():
    sdk = FakeSdk()
    sdk.errors["authorize_order"] = FakeApiError(422, '{"issue": "ORDER_NOT_APPROVED"}')
    raised(lambda: funder(sdk).confirm(PAYMENT), NotApprovedYet)

    other = FakeSdk()
    other.errors["authorize_order"] = FakeApiError(500)
    error = raised(lambda: funder(other).confirm(PAYMENT), FundingError)
    assert not isinstance(error, NotApprovedYet)


def test_capturing_returns_the_capture_and_insists_on_completed():
    sdk = FakeSdk()
    assert funder(sdk).capture(PAYMENT) == "CAP-1"
    assert sdk.calls[0][1]["authorization_id"] == "AUTH-1"

    pending = FakeSdk()
    pending.capture_status = "PENDING"
    assert "PENDING" in str(raised(lambda: funder(pending).capture(PAYMENT), FundingError))

    enum_like = FakeSdk()
    enum_like.capture_status = SimpleNamespace(value="COMPLETED")
    assert funder(enum_like).capture(PAYMENT) == "CAP-1"


def test_refunding_voids_an_uncaptured_hold_and_refunds_a_captured_one():
    sdk = FakeSdk()
    assert funder(sdk).refund(PAYMENT) == "VOIDED-AUTH-1"
    assert sdk.calls[0][0] == "void"

    captured = SimpleNamespace(**{**PAYMENT.__dict__, "paypal_capture_id": "CAP-1"})
    sdk = FakeSdk()
    assert funder(sdk).refund(captured) == "REFUNDED-REF-1"
    assert sdk.calls[0][0] == "refund"
    assert sdk.calls[0][1]["capture_id"] == "CAP-1"

    failing = FakeSdk()
    failing.errors["void"] = FakeApiError(400)
    raised(lambda: funder(failing).refund(PAYMENT), FundingError)


def test_paying_the_seller_sends_a_payout_and_waits_for_paypal():
    http = FakeHttp(polls=(("PENDING", "PENDING"), ("SUCCESS", "SUCCESS")))
    with Settings(paypal_payout_email="", paypal_client_id="id", paypal_client_secret="secret"):
        instance = funder(http=http)
        assert instance.payout(PAYMENT, SELLER) == "BATCH-1"

    token_call = http.calls[0]
    assert token_call[2]["auth"] == ("id", "secret")
    create = http.calls[1]
    assert create[1].endswith("/v1/payments/payouts")
    assert create[2]["headers"] == {"Authorization": "Bearer TOKEN"}
    item = create[2]["json"]["items"][0]
    assert item["receiver"] == "nova-seller@example.com"
    assert item["amount"] == {"value": "20.00", "currency": "USD"}
    batch_id = create[2]["json"]["sender_batch_header"]["sender_batch_id"]
    assert batch_id.startswith("horkos-7-")
    assert len(instance.slept) == 2  # it checked twice, then stopped


def test_the_demo_can_pay_every_seller_into_one_sandbox_account():
    http = FakeHttp()
    with Settings(paypal_payout_email="sb-demo@personal.example.com"):
        funder(http=http).payout(PAYMENT, SELLER)
    item = http.calls[1][2]["json"]["items"][0]
    assert item["receiver"] == "sb-demo@personal.example.com"


def test_a_failed_payout_or_a_refusal_from_paypal_is_a_funding_error():
    denied = FakeHttp(polls=(("PROCESSING", "DENIED"),))
    assert "DENIED" in str(raised(lambda: funder(http=denied).payout(PAYMENT, SELLER), FundingError))

    refused = FakeHttp(
        create_status=400,
        create_body={"name": "INSUFFICIENT_FUNDS", "message": "Not enough money."},
    )
    message = str(raised(lambda: funder(http=refused).payout(PAYMENT, SELLER), FundingError))
    assert "INSUFFICIENT_FUNDS" in message
