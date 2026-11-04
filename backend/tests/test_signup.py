from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.scripts.seed import seed_demo_data

# These tests use the real login check, not the demo-user shortcut.
pytestmark = pytest.mark.real_auth

SECRET = "a-long-secret-for-the-tests-0123456789"
GOOD = {
    "name": "  Wanjiru Kamau ",
    "email": " Wanjiru@Example.com ",
    "password": "a-good-password",
}


@pytest.fixture()
def api(monkeypatch):
    monkeypatch.setattr(settings, "jwt_secret", SECRET)
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

    def override_get_db():
        with factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    yield SimpleNamespace(client=TestClient(app), engine=engine)
    app.dependency_overrides.clear()


def sign_up(api, **changes):
    return api.client.post("/auth/signup", json={**GOOD, **changes})


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


def test_a_new_buyer_can_sign_up_and_is_signed_in(api):
    response = sign_up(api)
    assert response.status_code == 201
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["user"]["name"] == "Wanjiru Kamau"
    assert body["user"]["email"] == "wanjiru@example.com"
    assert body["user"]["role"] == "buyer"
    assert body["user"]["seller_id"] is None
    payments = api.client.get("/payments", headers=bearer(body["access_token"]))
    assert payments.status_code == 200
    assert payments.json()["total"] == 0


def test_the_new_account_can_log_in_afterwards(api):
    sign_up(api)
    login = {"email": "wanjiru@example.com", "password": "a-good-password"}
    assert api.client.post("/auth/login", json=login).status_code == 200
    wrong = {**login, "password": "not-the-password"}
    assert api.client.post("/auth/login", json=wrong).status_code == 401


def test_a_new_seller_gets_a_seller_record_with_no_trust(api):
    response = sign_up(
        api, role="seller", paypal_email=" Pay@Example.com ", name="Otieno Dev"
    )
    assert response.status_code == 201
    user = response.json()["user"]
    assert user["role"] == "seller"
    assert user["seller_id"] == "sel_otienodev"
    token = response.json()["access_token"]
    sellers = api.client.get("/sellers", headers=bearer(token)).json()
    assert sellers["total"] == 5
    mine = next(item for item in sellers["items"] if item["id"] == "sel_otienodev")
    assert mine["trust_score"] == 0
    assert mine["tier"] == "new"
    assert mine["limit_cents"] == 1000
    assert mine["paypal_email"] == "pay@example.com"
    assert api.client.get("/jobs", headers=bearer(token)).json()["total"] == 0


def test_a_seller_name_that_is_taken_gets_a_different_seller_id(api):
    response = sign_up(api, role="seller", paypal_email="pay@example.com", name="Nova")
    assert response.status_code == 201
    seller_id = response.json()["user"]["seller_id"]
    assert seller_id != "sel_nova"
    assert seller_id.startswith("sel_nova")


def test_an_email_that_is_taken_is_refused(api):
    assert sign_up(api).status_code == 201
    again = sign_up(api, email="WANJIRU@example.com")
    assert again.status_code == 409
    assert again.json()["error"]["code"] == "email_taken"
    assert sign_up(api, email="amara@example.com").status_code == 409


@pytest.mark.parametrize(
    "password",
    ["short", "        ", "wanjiru@example.com", "Wanjiru@Example.com"],
)
def test_weak_passwords_are_refused(api, password):
    response = sign_up(api, password=password)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert response.json()["error"]["message"].startswith("password:")


@pytest.mark.parametrize(
    "changes",
    [
        {"email": "not-an-email"},
        {"name": "   "},
        {"role": "admin"},
        {"role": "seller"},
        {"role": "seller", "paypal_email": "nope"},
    ],
)
def test_bad_input_is_refused(api, changes):
    response = sign_up(api, **changes)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"

def test_a_sign_up_that_cannot_make_a_token_saves_nothing(api, monkeypatch):
    monkeypatch.setattr(settings, "jwt_secret", "")
    client = TestClient(app, raise_server_exceptions=False)
    assert client.post("/auth/signup", json=GOOD).status_code == 500
    monkeypatch.setattr(settings, "jwt_secret", SECRET)
    login = {"email": "wanjiru@example.com", "password": "a-good-password"}
    assert api.client.post("/auth/login", json=login).status_code == 401