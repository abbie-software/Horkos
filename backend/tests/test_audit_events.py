import json
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.deps import (
    get_buyer_agent,
    get_funder,
    get_intent_checker,
    get_runner,
    get_session_factory,
    get_stream_settings,
)
from app.main import app
from app.models import AuditEntry
from app.scripts.seed import seed_demo_data
from app.services.buyer_agent import BuyerProposal
from app.services.funding import SimulatedFunder
from app.services.sandbox import SandboxResult
from app.services.signals import IntentResult
from app.services.streaming import StreamSettings

TEST_CODE = (
    "from solution import double\n"
    "\n"
    "def test_doubles_a_number():\n"
    "    assert double(2) == 4\n"
)
PASSED = SandboxResult(
    status="passed", passed=3, total=3, duration_ms=12, output_excerpt="3 passed in 0.01s"
)
FAILED = SandboxResult(
    status="failed", passed=1, failed=2, total=3, duration_ms=12,
    output_excerpt="2 failed, 1 passed.",
)
COULD_NOT_RUN = SandboxResult(status="error", output_excerpt="Docker is not installed.")
GOOD_CODE = 'def reverse_words(sentence):\n    return " ".join(reversed(sentence.split()))\n'


class FakeAgent:
    def __init__(self, amount_cents=2000):
        self.amount_cents = amount_cents

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


def make_engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        seed_demo_data(session)
        session.commit()
    return engine


@pytest.fixture()
def shop():
    engine = make_engine()
    agent, runner = FakeAgent(), FakeRunner(PASSED)
    factory = sessionmaker(bind=engine, expire_on_commit=False)

    def override_get_db():
        with factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_session_factory] = lambda: factory
    app.dependency_overrides[get_runner] = lambda: runner
    app.dependency_overrides[get_buyer_agent] = lambda: agent
    app.dependency_overrides[get_intent_checker] = lambda: FakeChecker()
    app.dependency_overrides[get_funder] = lambda: SimulatedFunder()
    app.dependency_overrides[get_stream_settings] = lambda: StreamSettings(
        poll_seconds=0.05, ping_seconds=0.1, max_seconds=0.4
    )
    yield SimpleNamespace(
        client=TestClient(app), engine=engine, agent=agent, runner=runner
    )
    app.dependency_overrides.clear()


def start_job(shop, **extra):
    return shop.client.post(
        "/jobs", json={"request_text": "Write a function that doubles a number.", **extra}
    )


def submit(shop, job="job_2002", seller="sel_kip"):
    return shop.client.post(
        f"/jobs/{job}/submission", json={"seller_id": seller, "content": GOOD_CODE}
    )


def audit(shop, payment=None):
    path = "/audit" if payment is None else f"/audit?payment_id={payment}"
    return shop.client.get(path).json()


def trail(shop, payment):
    """The audit entries for one payment, oldest first, as (actor, action, verdict)."""
    items = audit(shop, payment)["items"]
    return [(i["actor"], i["action"], i["verdict"]) for i in reversed(items)]


def feed(shop, last_id="evt_000"):
    """Every event the stream sends after last_id, as a list of dicts."""
    headers = {"Last-Event-ID": last_id} if last_id else {}
    text = shop.client.get("/events?token=demo", headers=headers).text
    return [json.loads(line[6:]) for line in text.splitlines() if line.startswith("data: ")]


# --- the audit trail --------------------------------------------------------


def test_the_seeded_audit_trail_is_listed_newest_first(shop):
    body = audit(shop)
    assert body["total"] == 12
    assert [i["id"] for i in body["items"]] == [
        "aud_009", "aud_008", "aud_007", "aud_006", "aud_005", "aud_004",
        "aud_003", "aud_002", "aud_001", "aud_012", "aud_011", "aud_010",
    ]


def test_the_audit_trail_can_be_filtered_to_one_payment(shop):
    body = audit(shop, "pay_1001")
    assert body["total"] == 5
    assert {i["payment_id"] for i in body["items"]} == {"pay_1001"}
    assert body["items"][0]["action"] == "Released payment"


def test_an_unknown_or_malformed_filter_gives_an_empty_list(shop):
    for payment in ("pay_9999", "banana", "job_2003"):
        assert audit(shop, payment) == {"items": [], "total": 0}


def test_an_audit_entry_has_the_contract_shape(shop):
    entry = next(i for i in audit(shop)["items"] if i["id"] == "aud_007")
    assert entry == {
        "id": "aud_007",
        "payment_id": "pay_1003",
        "at": "2026-10-20T10:00:03Z",
        "actor": "guard",
        "action": "Reviewed the payment",
        "verdict": "ask",
        "reason": "New seller with no history, and the amount is above their limit.",
        "details": {"risk_score": 48},
    }


def test_seeding_twice_adds_no_audit_entries(shop):
    with Session(shop.engine) as db:
        assert seed_demo_data(db) == []
        db.commit()
        assert db.scalar(select(func.count()).select_from(AuditEntry)) == 12


# --- what a job leaves behind -----------------------------------------------


def test_a_clean_job_leaves_a_trail_and_four_feed_events(shop):
    start_job(shop)
    assert trail(shop, "pay_1007") == [
        ("buyer_agent", "Proposed a payment", None),
        ("guard", "Reviewed the payment", "approve"),
        ("system", "Secured funds", None),
    ]
    events = feed(shop)
    assert [e["type"] for e in events] == [
        "payment.proposed",
        "payment.verdict",
        "payment.status_changed",
        "payment.status_changed",
    ]
    assert [e["message"] for e in events] == [
        "Buyer Agent proposed paying $20.00 to Nova Scripts.",
        "Guard approved the payment (low risk).",
        "Payment approved.",
        "Funds are being held.",
    ]
    assert events[0]["payload"] == {"amount_cents": 2000}
    assert events[1]["payload"]["verdict"] == "approve"
    assert events[3]["payload"] == {"from": "approved", "to": "held"}
    assert {e["payment_id"] for e in events} == {"pay_1007"}
    assert {e["seller_id"] for e in events} == {"sel_nova"}


def test_a_blocked_payment_is_recorded_with_its_rule(shop):
    shop.agent.amount_cents = 50000
    start_job(shop)
    verdict = next(e for e in feed(shop) if e["type"] == "payment.verdict")
    assert verdict["message"] == "Guard blocked the payment: over your spending cap."
    assert verdict["payload"] == {
        "verdict": "block",
        "risk_level": "high",
        "risk_score": 92,
        "hard_rule": "over_cap",
    }
    review = next(i for i in audit(shop, "pay_1007")["items"] if i["actor"] == "guard")
    assert review["verdict"] == "block"
    assert review["details"] == {"risk_score": 92, "hard_rule": "over_cap"}


def test_an_ask_and_the_users_answer_are_recorded(shop):
    shop.agent.amount_cents = 2500
    start_job(shop, seller_id="sel_zed")
    assert trail(shop, "pay_1007") == [
        ("buyer_agent", "Proposed a payment", None),
        ("guard", "Reviewed the payment", "ask"),
    ]
    assert [e["message"] for e in feed(shop)][-1] == "Waiting for your decision."

    shop.client.post("/payments/pay_1007/decision", json={"decision": "approve"})
    assert trail(shop, "pay_1007")[2:] == [
        ("user", "Approved the payment", None),
        ("system", "Secured funds", None),
    ]
    assert [e["message"] for e in feed(shop)][-2:] == [
        "Payment approved.",
        "Funds are being held.",
    ]


# --- what settling a payment leaves behind ----------------------------------


def test_paying_good_work_is_recorded(shop):
    assert submit(shop).status_code == 202
    events = feed(shop)
    assert [e["type"] for e in events] == [
        "verification.result",
        "payment.status_changed",
        "payment.status_changed",
        "trust.updated",
    ]
    assert events[0]["message"] == "Work passed 3 of 3 tests."
    assert events[0]["payload"] == {"passed": True, "tests_passed": 3, "tests_total": 3}
    assert events[2]["message"] == "Kip Codes was paid $15.00."
    assert events[3]["message"] == "Kip Codes's trust rose from 46 to 58. New limit: $25.00."
    assert events[3]["payload"] == {"old_score": 46, "new_score": 58, "new_limit_cents": 2500}
    assert {e["seller_id"] for e in events} == {"sel_kip"}

    assert trail(shop, "pay_1002") == [
        ("verifier", "Checked the work", None),
        ("system", "Released payment", None),
        ("system", "Raised trust", None),
    ]


def test_refunding_wrong_work_is_recorded(shop):
    shop.runner.result = FAILED
    submit(shop)
    events = feed(shop)
    assert [e["type"] for e in events] == [
        "verification.result",
        "payment.status_changed",
        "trust.updated",
    ]
    assert events[0]["message"] == "Work failed: 1 of 3 tests passed."
    assert events[0]["payload"]["passed"] is False
    assert events[1]["message"] == "$15.00 was refunded to the buyer."
    assert events[2]["message"] == "Kip Codes's trust dropped from 46 to 24. New limit: $5.00."

    entries = audit(shop, "pay_1002")["items"]
    check = next(i for i in entries if i["actor"] == "verifier")
    assert check["reason"] == "1 of 3 tests passed. The work did not meet the agreed tests."
    assert [i["action"] for i in reversed(entries)] == [
        "Checked the work",
        "Refunded the buyer",
        "Lowered trust",
    ]


def test_a_runner_that_cannot_decide_leaves_only_an_audit_note(shop):
    shop.runner.result = COULD_NOT_RUN
    submit(shop)
    assert feed(shop) == []
    assert trail(shop, "pay_1002") == [("system", "Could not check the work", None)]


# --- the live stream --------------------------------------------------------


def test_events_have_the_contract_shape(shop):
    start_job(shop)
    event = feed(shop)[0]
    assert set(event) == {"id", "type", "at", "payment_id", "seller_id", "message", "payload"}
    assert event["id"] == "evt_001"
    assert event["at"].endswith("Z")


def test_a_new_connection_starts_from_now(shop):
    start_job(shop)
    response = shop.client.get("/events?token=demo")
    assert response.headers["content-type"].startswith("text/event-stream")
    assert response.text.startswith(": connected")
    assert "data:" not in response.text


def test_a_reconnecting_browser_gets_only_what_it_missed_and_keep_alives(shop):
    start_job(shop)
    text = shop.client.get("/events", headers={"Last-Event-ID": "evt_002"}).text
    ids = [line for line in text.splitlines() if line.startswith("id: ")]
    assert ids == ["id: evt_003", "id: evt_004"]
    assert ": ping" in text
