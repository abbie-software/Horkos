from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.deps import get_buyer_agent, get_funder, get_intent_checker
from app.main import app
from app.models import Job, User
from app.scripts.seed import seed_demo_data
from app.services.buyer_agent import BuyerAgentError, BuyerProposal
from app.services.funding import SimulatedFunder
from app.services.signals import IntentResult

REQUEST = "Write a Python function that converts a CSV file into JSON."
ZED_ASK_REASON = (
    "I need your approval: Zed Dev is new with no delivery history, "
    "and $25.00 is above their current limit of $10.00."
)


class FakeAgent:
    def __init__(self, amount_cents=2000, category="coding", error=None):
        self.amount_cents, self.category, self.error = amount_cents, category, error
        self.calls = 0

    def propose(self, request_text):
        self.calls += 1
        if self.error:
            raise self.error
        return BuyerProposal(
            category=self.category,
            amount_cents=self.amount_cents,
            description="A small Python function.",
            acceptance_tests=["Works on a simple input", "Handles empty input", "Fails clearly on bad input"],
        )


class FakeChecker:
    def __init__(self, mismatch=False):
        self.mismatch = mismatch

    def check(self, request_text, payment_summary):
        return IntentResult(mismatch=self.mismatch, detail="")


def make_engine(seed=True):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        if seed:
            seed_demo_data(session)
        else:
            session.add(User(email="amara@example.com", name="Amara"))
        session.commit()
    return engine


def install(engine, agent, checker):
    def override_get_db():
        with Session(engine, expire_on_commit=False) as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_buyer_agent] = lambda: agent
    app.dependency_overrides[get_intent_checker] = lambda: checker
    app.dependency_overrides[get_funder] = lambda: SimulatedFunder()
    return TestClient(app)


@pytest.fixture()
def world():
    engine = make_engine()
    agent, checker = FakeAgent(), FakeChecker()
    client = install(engine, agent, checker)
    yield SimpleNamespace(client=client, engine=engine, agent=agent, checker=checker)
    app.dependency_overrides.clear()


def start_job(world, **extra):
    return world.client.post("/jobs", json={"request_text": REQUEST, **extra})


def job_status(world, job_number):
    with Session(world.engine) as db:
        return db.get(Job, job_number).status


def test_a_clean_job_goes_to_the_most_trusted_seller_and_is_held(world):
    response = start_job(world)
    assert response.status_code == 201
    body = response.json()
    assert body["job"]["id"] == "job_2007"
    assert body["job"]["seller_id"] == "sel_nova"
    assert body["job"]["status"] == "awaiting_work"
    assert body["job"]["category"] == "coding"
    assert body["job"]["payment_id"] == body["payment"]["id"] == "pay_1007"
    assert len(body["job"]["acceptance_tests"]) == 3

    payment = body["payment"]
    assert payment["status"] == "held"
    assert payment["decision"]["verdict"] == "approve"
    assert [h["status"] for h in payment["history"]] == ["proposed", "approved", "held"]
    assert payment["paypal"]["funding_ref"] == "SIM-FUND-1007"

    newest = world.client.get("/payments").json()["items"][0]
    assert newest["id"] == "pay_1007"
    assert newest["job_id"] == "job_2007"


def test_a_new_seller_above_their_limit_makes_the_guard_ask(world):
    world.agent.amount_cents = 2500
    payment = start_job(world, seller_id="sel_zed").json()["payment"]
    assert payment["status"] == "awaiting_user"
    assert payment["decision"]["verdict"] == "ask"
    assert payment["decision"]["reason"] == ZED_ASK_REASON
    assert [h["status"] for h in payment["history"]] == ["proposed", "awaiting_user"]
    assert job_status(world, 2007) == "open"


def test_a_payment_over_the_cap_is_blocked_and_the_job_cancelled(world):
    world.agent.amount_cents = 50000
    payment = start_job(world).json()["payment"]
    assert payment["status"] == "blocked"
    assert payment["decision"]["verdict"] == "block"
    assert payment["decision"]["hard_rule"] == "over_cap"
    assert job_status(world, 2007) == "cancelled"


def test_the_user_approves_an_ask_and_the_money_is_held(world):
    world.agent.amount_cents = 2500
    start_job(world, seller_id="sel_zed")
    response = world.client.post("/payments/pay_1007/decision", json={"decision": "approve"})
    assert response.status_code == 200
    payment = response.json()
    assert payment["status"] == "held"
    assert [h["status"] for h in payment["history"]] == [
        "proposed", "awaiting_user", "approved", "held",
    ]
    assert payment["paypal"]["funding_ref"] == "SIM-FUND-1007"
    assert payment["decision"]["verdict"] == "ask"
    assert job_status(world, 2007) == "awaiting_work"


def test_the_user_rejects_an_ask(world):
    world.agent.amount_cents = 2500
    start_job(world, seller_id="sel_zed")
    payment = world.client.post(
        "/payments/pay_1007/decision", json={"decision": "reject"}
    ).json()
    assert payment["status"] == "blocked"
    assert payment["history"][-1]["note"] == "You rejected the payment."
    assert job_status(world, 2007) == "cancelled"


def test_a_payment_can_only_be_decided_once(world):
    world.agent.amount_cents = 2500
    start_job(world, seller_id="sel_zed")
    world.client.post("/payments/pay_1007/decision", json={"decision": "approve"})
    again = world.client.post("/payments/pay_1007/decision", json={"decision": "reject"})
    assert again.status_code == 409
    assert again.json()["error"] == {
        "code": "invalid_state",
        "message": "This payment has already been decided.",
    }


def test_decision_errors_use_the_contract_shape(world):
    missing = world.client.post("/payments/pay_9999/decision", json={"decision": "approve"})
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "not_found"
    bad = world.client.post("/payments/pay_1003/decision", json={"decision": "maybe"})
    assert bad.status_code == 422
    assert bad.json()["error"]["code"] == "validation_error"


def test_an_unknown_seller_is_rejected_before_the_agent_is_asked(world):
    response = start_job(world, seller_id="sel_nobody")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
    assert world.agent.calls == 0


def test_a_blank_request_is_rejected(world):
    for text in ("", "   "):
        response = world.client.post("/jobs", json={"request_text": text})
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "validation_error"
    assert world.agent.calls == 0


def test_a_buyer_agent_failure_is_a_clean_error_and_creates_nothing(world):
    world.agent.error = BuyerAgentError("The Buyer Agent could not prepare a proposal.")
    response = start_job(world)
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "server_error"
    assert world.client.get("/payments").json()["total"] == 6


def test_starting_a_job_needs_a_saved_oath():
    engine = make_engine(seed=False)
    agent = FakeAgent()
    client = install(engine, agent, FakeChecker())
    try:
        response = client.post("/jobs", json={"request_text": REQUEST})
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "invalid_state"
    assert agent.calls == 0


def test_an_unsure_auditor_makes_the_guard_ask(world):
    world.checker.mismatch = None
    payment = start_job(world).json()["payment"]
    assert payment["status"] == "awaiting_user"
    assert "could not check" in payment["decision"]["reason"]


def test_a_retry_right_after_a_block_triggers_the_velocity_signal(world):
    world.agent.amount_cents = 50000
    assert start_job(world).json()["payment"]["status"] == "blocked"
    world.agent.amount_cents = 2000
    payment = start_job(world).json()["payment"]
    velocity = next(s for s in payment["decision"]["signals"] if s["code"] == "velocity")
    assert velocity["triggered"] is True
    assert payment["status"] == "held"


def test_the_daily_cap_counts_payments_already_approved_today(world):
    world.agent.amount_cents = 3000
    for _ in range(3):
        assert start_job(world).json()["payment"]["status"] == "held"
    fourth = start_job(world).json()["payment"]
    assert fourth["status"] == "blocked"
    assert fourth["decision"]["hard_rule"] == "over_cap"
    assert "daily cap" in fourth["decision"]["reason"]