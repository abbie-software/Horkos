from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.deps import (
    get_attack_pause,
    get_buyer_agent,
    get_demo_enabled,
    get_funder,
    get_intent_checker,
    get_runner,
    get_session_factory,
    get_stream_settings,
)
from app.main import app
from app.models import Job, Payment
from app.scripts.seed import seed_demo_data
from app.services.buyer_agent import BuyerProposal
from app.services.funding import (
    FundingError,
    FundingStart,
    NotApprovedYet,
    SimulatedFunder,
)
from app.services.paypal_funder import PayPalFunder
from app.services.sandbox import SandboxResult
from app.services.signals import IntentResult
from app.services.streaming import StreamSettings

TEST_CODE = (
    "from solution import double\n"
    "\n"
    "def test_doubles_a_number():\n"
    "    assert double(2) == 4\n"
)
GOOD_CODE = "def double(n):\n    return n * 2\n"
PASSED = SandboxResult(status="passed", passed=1, total=1, duration_ms=5)
FAILED = SandboxResult(status="failed", passed=0, failed=1, total=1, duration_ms=5)


class FakeFunder:
    """Behaves like the PayPal funder: the buyer must approve before money is held."""

    def __init__(self):
        self.calls = []
        self.approved = False
        self.fail = set()

    def start(self, payment, seller):
        self.calls.append("start")
        if "start" in self.fail:
            raise FundingError("PayPal is down")
        return FundingStart(
            ref=f"ORDER-{payment.id}",
            held=False,
            approve_url=f"https://paypal.test/approve/{payment.id}",
        )

    def confirm(self, payment):
        self.calls.append("confirm")
        if not self.approved:
            raise NotApprovedYet("not yet")
        return f"AUTH-{payment.id}"

    def capture(self, payment):
        self.calls.append("capture")
        return f"CAP-{payment.id}"

    def payout(self, payment, seller):
        self.calls.append("payout")
        if "payout" in self.fail:
            raise FundingError("payout is down")
        return f"PAYOUT-{payment.id}"

    def refund(self, payment):
        self.calls.append("refund")
        return f"REFUND-{payment.id}"


class FakeAgent:
    def __init__(self):
        self.amount_cents = 2000

    def propose(self, request_text):
        return BuyerProposal(
            category="coding",
            amount_cents=self.amount_cents,
            description="A small Python function.",
            acceptance_tests=["Define double(n) that returns n times two"],
            test_code=TEST_CODE,
        )


class FakeChecker:
    def check(self, request_text, payment_summary):
        return IntentResult(mismatch=False, detail="")


class FakeRunner:
    def __init__(self, result):
        self.result = result

    def __call__(self, content, test_code):
        return self.result


@pytest.fixture()
def shop():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        seed_demo_data(session)
        session.commit()
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    funder, agent, runner = FakeFunder(), FakeAgent(), FakeRunner(PASSED)

    def override_get_db():
        with factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_session_factory] = lambda: factory
    app.dependency_overrides[get_runner] = lambda: runner
    app.dependency_overrides[get_buyer_agent] = lambda: agent
    app.dependency_overrides[get_intent_checker] = lambda: FakeChecker()
    app.dependency_overrides[get_funder] = lambda: funder
    app.dependency_overrides[get_demo_enabled] = lambda: True
    app.dependency_overrides[get_attack_pause] = lambda: 0.0
    app.dependency_overrides[get_stream_settings] = lambda: StreamSettings(
        poll_seconds=0.05, ping_seconds=5.0, max_seconds=0.2
    )
    yield SimpleNamespace(
        client=TestClient(app), engine=engine, funder=funder, agent=agent, runner=runner
    )
    app.dependency_overrides.clear()


def start_job(shop, **extra):
    return shop.client.post(
        "/jobs", json={"request_text": "Write a function that doubles a number.", **extra}
    )


def confirm(shop, number=1007):
    return shop.client.post(f"/payments/pay_{number}/funding/confirm")


def payment(shop, number=1007):
    return shop.client.get(f"/payments/pay_{number}").json()


def submit(shop, job="job_2007", seller="sel_nova"):
    return shop.client.post(
        f"/jobs/{job}/submission", json={"seller_id": seller, "content": GOOD_CODE}
    )


def stored(shop, model, number, attribute):
    with Session(shop.engine) as db:
        return getattr(db.get(model, number), attribute)


def fund(shop):
    """Start a job and play the buyer approving it on PayPal."""
    start_job(shop)
    shop.funder.approved = True
    assert confirm(shop).status_code == 200


def test_an_approved_payment_waits_for_the_buyer_to_fund_it(shop):
    body = start_job(shop).json()
    result = body["payment"]
    assert result["status"] == "approved"
    assert result["paypal"]["approve_url"] == "https://paypal.test/approve/1007"
    assert result["paypal"]["funding_ref"] == "ORDER-1007"
    assert [h["status"] for h in result["history"]] == ["proposed", "approved"]
    assert body["job"]["status"] == "open"
    assert shop.funder.calls == ["start"]


def test_confirming_before_the_buyer_approves_is_refused(shop):
    start_job(shop)
    response = confirm(shop)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert "has not approved" in response.json()["error"]["message"]
    assert payment(shop)["status"] == "approved"


def test_confirming_after_the_buyer_approves_holds_the_money(shop):
    start_job(shop)
    shop.funder.approved = True
    response = confirm(shop)
    assert response.status_code == 200
    held = response.json()
    assert held["status"] == "held"
    assert held["paypal"]["approve_url"] is None
    assert held["paypal"]["funding_ref"] == "AUTH-1007"
    assert held["history"][-1]["note"] == "Funds secured."
    assert stored(shop, Job, 2007, "status") == "awaiting_work"

    trail = shop.client.get("/audit?payment_id=pay_1007").json()["items"]
    assert [i["action"] for i in reversed(trail)] == [
        "Proposed a payment",
        "Reviewed the payment",
        "Asked the buyer to fund the payment",
        "Secured funds",
    ]


def test_only_a_payment_waiting_for_funding_can_be_confirmed(shop):
    fund(shop)
    again = confirm(shop)
    assert again.status_code == 409
    assert again.json()["error"] == {
        "code": "invalid_state",
        "message": "This payment is not waiting for funding.",
    }
    assert confirm(shop, 1002).status_code == 409  # a seeded payment that is already held
    assert confirm(shop, 9999).status_code == 404


def test_an_ask_the_user_approves_then_waits_for_funding_like_any_other(shop):
    shop.agent.amount_cents = 2500
    asked = start_job(shop, seller_id="sel_zed").json()["payment"]
    assert asked["status"] == "awaiting_user"
    assert shop.funder.calls == []

    approved = shop.client.post("/payments/pay_1007/decision", json={"decision": "approve"})
    assert approved.json()["status"] == "approved"
    assert approved.json()["paypal"]["approve_url"] == "https://paypal.test/approve/1007"

    shop.funder.approved = True
    assert confirm(shop).json()["status"] == "held"


def test_good_work_is_captured_and_then_the_seller_is_paid(shop):
    fund(shop)
    assert submit(shop).status_code == 202
    result = payment(shop)
    assert result["status"] == "released"
    assert result["paypal"]["payout_ref"] == "PAYOUT-1007"
    assert shop.funder.calls == ["start", "confirm", "capture", "payout"]
    assert stored(shop, Payment, 1007, "paypal_capture_id") == "CAP-1007"


def test_failed_work_gives_the_buyer_their_money_back(shop):
    shop.runner.result = FAILED
    fund(shop)
    submit(shop)
    result = payment(shop)
    assert result["status"] == "refunded"
    assert result["paypal"]["refund_ref"] == "REFUND-1007"
    assert shop.funder.calls == ["start", "confirm", "refund"]


def test_a_failed_payout_keeps_the_money_held_and_a_retry_never_captures_twice(shop):
    fund(shop)
    shop.funder.fail = {"payout"}
    assert submit(shop).status_code == 202
    assert payment(shop)["status"] == "held"
    assert stored(shop, Job, 2007, "status") == "awaiting_work"
    assert stored(shop, Payment, 1007, "paypal_capture_id") == "CAP-1007"
    assert stored(shop, Payment, 1007, "payout_ref") is None

    shop.funder.fail = set()
    assert submit(shop).status_code == 202
    assert payment(shop)["status"] == "released"
    assert shop.funder.calls.count("capture") == 1
    assert shop.funder.calls.count("payout") == 2


def test_if_paypal_is_down_at_the_start_nothing_is_created(shop):
    shop.funder.fail = {"start"}
    response = start_job(shop)
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "server_error"
    assert shop.client.get("/payments").json()["total"] == 6


def test_the_red_team_always_plays_with_simulated_money(shop):
    shop.runner.result = FAILED
    assert shop.client.post("/demo/attack/bad_work").status_code == 202
    newest = shop.client.get("/payments").json()["items"][0]
    assert newest["status"] == "refunded"
    assert newest["paypal"]["refund_ref"].startswith("SIM-")
    assert shop.funder.calls == []


def test_the_setting_chooses_between_simulated_and_sandbox_money():
    before = settings.paypal_funding
    try:
        settings.paypal_funding = "simulated"
        assert isinstance(get_funder(), SimulatedFunder)
        settings.paypal_funding = "sandbox"
        assert isinstance(get_funder(), PayPalFunder)
    finally:
        settings.paypal_funding = before
