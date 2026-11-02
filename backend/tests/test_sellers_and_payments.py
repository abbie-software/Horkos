import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import Payment, PaymentEvent, Seller
from app.scripts.seed import seed_demo_data
from app.services.ledger import create_payment


@pytest.fixture()
def engine():
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
def client(engine):
    def override_get_db():
        with Session(engine, expire_on_commit=False) as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_sellers_match_the_contract_seed(client):
    body = client.get("/sellers").json()
    assert body["total"] == 4
    assert [s["id"] for s in body["items"]] == [
        "sel_nova",
        "sel_kip",
        "sel_zed",
        "sel_quick",
    ]
    assert body["items"][0] == {
        "id": "sel_nova",
        "name": "Nova Scripts",
        "paypal_email": "nova-seller@example.com",
        "trust_score": 82,
        "tier": "trusted",
        "limit_cents": 5000,
        "jobs_completed": 5,
        "jobs_failed": 0,
        "last_activity_at": "2026-10-20T09:12:41Z",
    }


def test_tiers_and_missing_activity(client):
    items = client.get("/sellers").json()["items"]
    assert [s["tier"] for s in items] == ["trusted", "building", "new", "restricted"]
    assert items[2]["last_activity_at"] is None


def test_payments_come_back_newest_first(client):
    body = client.get("/payments").json()
    assert body["total"] == 6
    assert [p["id"] for p in body["items"]] == [
        "pay_1005",
        "pay_1004",
        "pay_1003",
        "pay_1002",
        "pay_1001",
        "pay_1006",
    ]


def test_filter_payments_by_status(client):
    body = client.get("/payments", params={"status": "held"}).json()
    assert [p["id"] for p in body["items"]] == ["pay_1002"]
    assert body["total"] == 1


def test_an_unknown_status_filter_is_a_contract_shaped_422(client):
    response = client.get("/payments", params={"status": "nonsense"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_payment_waiting_for_the_user(client):
    body = client.get("/payments/pay_1003").json()
    assert body["status"] == "awaiting_user"
    assert body["job_id"] == "job_2003"
    assert body["seller_id"] == "sel_zed"
    assert body["seller_name"] == "Zed Dev"
    assert body["amount_cents"] == 2500
    assert body["currency"] == "USD"
    assert body["decision"]["verdict"] == "ask"
    assert body["decision"]["risk_level"] == "medium"
    assert len(body["decision"]["signals"]) == 6
    triggered = {s["code"] for s in body["decision"]["signals"] if s["triggered"]}
    assert triggered == {"unproven_seller", "edge_of_limit"}
    assert [h["status"] for h in body["history"]] == ["proposed", "awaiting_user"]
    assert body["paypal"] == {
        "funding_ref": None,
        "payout_ref": None,
        "refund_ref": None,
        "approve_url": None,
    }

def test_released_payment_has_its_history_and_paypal_refs(client):
    body = client.get("/payments/pay_1001").json()
    assert [h["status"] for h in body["history"]] == [
        "proposed",
        "approved",
        "held",
        "verified",
        "released",
    ]
    assert body["history"][0]["at"] == "2026-10-20T09:00:00Z"
    assert body["paypal"]["funding_ref"] == "MOCK-FUND-1001"
    assert body["paypal"]["payout_ref"] == "MOCK-PAYOUT-1001"
    assert body["created_at"] == "2026-10-20T09:00:00Z"
    assert body["updated_at"] == "2026-10-20T09:12:41Z"


def test_refunded_payment_and_blocked_payment_details(client):
    refunded = client.get("/payments/pay_1006").json()
    assert refunded["status"] == "refunded"
    assert refunded["paypal"]["refund_ref"] == "MOCK-REFUND-1006"

    blocked = client.get("/payments/pay_1005").json()
    assert blocked["status"] == "blocked"
    assert blocked["decision"]["verdict"] == "block"
    assert blocked["decision"]["hard_rule"] == "recipient_changed"


def test_an_unknown_payment_is_a_contract_shaped_404(client):
    for public_id in ("pay_9999", "banana", "pay_", "job_2003"):
        response = client.get(f"/payments/{public_id}")
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "not_found"


def test_a_payment_with_no_stored_decision_asks_the_user(client, engine):
    with Session(engine) as db:
        payment = create_payment(
            db, user_id=1, seller_id=3, amount_cents=1000, description="No decision yet"
        )
        db.commit()
        public_id = f"pay_{payment.id}"
    body = client.get(f"/payments/{public_id}").json()
    assert body["job_id"] is None
    assert body["decision"]["verdict"] == "ask"
    assert len(body["decision"]["signals"]) == 6


def test_seeding_twice_adds_nothing_new(engine):
    with Session(engine) as db:
        assert seed_demo_data(db) == []
        db.commit()
        assert db.scalar(select(func.count()).select_from(Payment)) == 6
        assert db.scalar(select(func.count()).select_from(Seller)) == 4
        assert db.scalar(select(func.count()).select_from(PaymentEvent)) == 18