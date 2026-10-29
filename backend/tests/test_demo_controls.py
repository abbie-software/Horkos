import json
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, update
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.deps import (
    get_attack_pause,
    get_demo_enabled,
    get_funder,
    get_runner,
    get_session_factory,
    get_stream_settings,
)
from app.main import app
from app.models import Seller
from app.scripts.seed import seed_demo_data
from app.services.attack_scripts import ATTACK_TEST_CODE, BAD_WORK_CODE
from app.services.funding import SimulatedFunder
from app.services.sandbox import SandboxResult
from app.services.streaming import StreamSettings

PASSED = SandboxResult(
    status="passed", passed=3, total=3, duration_ms=12, output_excerpt="3 passed in 0.01s"
)
FAILED = SandboxResult(
    status="failed", passed=1, failed=2, total=3, duration_ms=12,
    output_excerpt="2 failed, 1 passed.",
)
GOOD_CODE = 'def reverse_words(sentence):\n    return " ".join(reversed(sentence.split()))\n'


class FakeRunner:
    def __init__(self, result):
        self.result, self.calls = result, []

    def __call__(self, content, test_code):
        self.calls.append((content, test_code))
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
    runner = FakeRunner(FAILED)
    factory = sessionmaker(bind=engine, expire_on_commit=False)

    def override_get_db():
        with factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_session_factory] = lambda: factory
    app.dependency_overrides[get_runner] = lambda: runner
    app.dependency_overrides[get_funder] = lambda: SimulatedFunder()
    app.dependency_overrides[get_attack_pause] = lambda: 0.0
    app.dependency_overrides[get_demo_enabled] = lambda: True
    app.dependency_overrides[get_stream_settings] = lambda: StreamSettings(
        poll_seconds=0.05, ping_seconds=5.0, max_seconds=0.3
    )
    yield SimpleNamespace(client=TestClient(app), engine=engine, runner=runner)
    app.dependency_overrides.clear()


def attack(shop, kind):
    return shop.client.post(f"/demo/attack/{kind}")


def newest(shop, count=1):
    return shop.client.get("/payments").json()["items"][:count]


def feed(shop):
    text = shop.client.get("/events", headers={"Last-Event-ID": "evt_000"}).text
    return [json.loads(line[6:]) for line in text.splitlines() if line.startswith("data: ")]


def signal(payment, code):
    return next(s for s in payment["decision"]["signals"] if s["code"] == code)


def test_changing_the_recipient_is_blocked_and_announced(shop):
    response = attack(shop, "recipient_change")
    assert response.status_code == 202
    assert response.json() == {
        "attack_id": "atk_4001",
        "type": "recipient_change",
        "status": "started",
    }

    (payment,) = newest(shop)
    assert payment["status"] == "blocked"
    assert payment["seller_id"] == "sel_nova"
    assert payment["decision"]["hard_rule"] == "recipient_changed"

    events = feed(shop)
    assert events[0]["type"] == "demo.attack_started"
    assert events[0]["message"] == "Red Team: attempting to change the recipient mid-job."
    assert events[0]["payload"] == {"attack": "recipient_change"}
    assert events[0]["payment_id"] is None
    verdict = next(e for e in events if e["type"] == "payment.verdict")
    assert verdict["message"] == "Guard blocked the payment: recipient changed mid-job."
    assert verdict["payload"] == {
        "verdict": "block",
        "risk_level": "high",
        "risk_score": 97,
        "hard_rule": "recipient_changed",
    }


def test_a_payment_far_over_the_cap_is_blocked(shop):
    attack(shop, "over_limit")
    (payment,) = newest(shop)
    assert payment["status"] == "blocked"
    assert payment["seller_id"] == "sel_zed"
    assert payment["decision"]["hard_rule"] == "over_cap"
    assert payment["decision"]["reason"].startswith(
        "Blocked: $500.00 is above your $50.00 per-job cap."
    )


def test_just_under_the_cap_from_a_new_seller_makes_the_guard_ask(shop):
    attack(shop, "edge_of_limit")
    (payment,) = newest(shop)
    assert payment["status"] == "awaiting_user"
    assert payment["decision"]["verdict"] == "ask"
    assert payment["decision"]["risk_level"] == "medium"
    assert signal(payment, "edge_of_limit")["triggered"] is True
    assert "$49.00 is above your $30.00 approval threshold" in payment["decision"]["reason"]


def test_rapid_retries_trigger_the_velocity_signal(shop):
    attack(shop, "rapid_retries")
    payments = newest(shop, 3)
    assert [p["amount_cents"] for p in payments] == [500, 45000, 50000]
    assert [p["status"] for p in payments] == ["awaiting_user", "blocked", "blocked"]
    assert signal(payments[0], "velocity")["triggered"] is True


def test_a_pushy_message_is_blocked_on_risk_and_shows_the_signal(shop):
    attack(shop, "pressure_language")
    (payment,) = newest(shop)
    assert payment["status"] == "blocked"
    assert payment["decision"]["hard_rule"] is None
    assert payment["decision"]["risk_score"] == 80
    assert signal(payment, "pressure_language")["triggered"] is True
    assert payment["decision"]["reason"].startswith(
        "Blocked: the risk score is 80 out of 100."
    )


def test_bad_work_fails_the_tests_refunds_the_buyer_and_cuts_trust(shop):
    attack(shop, "bad_work")
    (payment,) = newest(shop)
    assert payment["status"] == "refunded"
    assert payment["seller_id"] == "sel_nova"
    assert payment["history"][-1]["note"] == (
        "2 of 3 tests failed. You were refunded. Trust score 82 to 60."
    )
    assert shop.runner.calls == [(BAD_WORK_CODE, ATTACK_TEST_CODE)]

    types = [e["type"] for e in feed(shop)]
    assert "verification.result" in types
    assert "trust.updated" in types
    nova = next(s for s in shop.client.get("/sellers").json()["items"] if s["id"] == "sel_nova")
    assert nova["trust_score"] == 60


def test_a_bad_work_attack_the_guard_stops_never_reaches_verification(shop):
    with Session(shop.engine) as db:
        db.execute(update(Seller).values(limit_cents=500))
        db.commit()
    attack(shop, "bad_work")
    (payment,) = newest(shop)
    assert payment["status"] == "awaiting_user"
    assert shop.runner.calls == []


def test_unknown_attacks_are_refused_and_each_attack_gets_its_own_id(shop):
    unknown = attack(shop, "nonsense")
    assert unknown.status_code == 422
    assert unknown.json()["error"]["code"] == "validation_error"
    assert attack(shop, "over_limit").json()["attack_id"] == "atk_4001"
    assert attack(shop, "over_limit").json()["attack_id"] == "atk_4002"


def test_the_demo_controls_can_be_switched_off(shop):
    app.dependency_overrides[get_demo_enabled] = lambda: False
    assert attack(shop, "over_limit").status_code == 404
    assert shop.client.post("/demo/reset").status_code == 404
    assert shop.client.get("/payments").json()["total"] == 6


def test_reset_restores_the_starting_data_and_keeps_the_feed_counting(shop):
    attack(shop, "over_limit")
    assert shop.client.get("/payments").json()["total"] == 7

    response = shop.client.post("/demo/reset")
    assert response.status_code == 204
    assert response.content == b""

    assert shop.client.get("/payments").json()["total"] == 6
    sellers = {s["id"]: s for s in shop.client.get("/sellers").json()["items"]}
    assert sellers["sel_nova"]["trust_score"] == 82
    assert shop.client.get("/audit").json()["total"] == 12
    assert shop.client.get("/oath").status_code == 200

    events = feed(shop)
    assert events[-1]["type"] == "demo.reset"
    assert events[-1]["message"] == "The demo was reset to its starting data."
    assert events[-1]["payload"] == {}
    assert all(e["payment_id"] is None and e["seller_id"] is None for e in events[:-1])
    numbers = [int(e["id"][4:]) for e in events]
    assert numbers == sorted(numbers)


def test_after_a_reset_the_held_demo_job_can_be_paid_again(shop):
    shop.client.post("/demo/reset")
    shop.runner.result = PASSED
    response = shop.client.post(
        "/jobs/job_2002/submission",
        json={"seller_id": "sel_kip", "content": GOOD_CODE},
    )
    assert response.status_code == 202
    payment = shop.client.get("/payments/pay_1002").json()
    assert payment["status"] == "released"
