from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.deps import get_demo_enabled, get_session_factory, get_stream_settings
from app.main import app
from app.models import User
from app.scripts.seed import seed_demo_data
from app.services.streaming import StreamSettings
from app.services.tokens import issue_token, read_token

# These tests use the real login check, not the demo-user shortcut.
pytestmark = pytest.mark.real_auth

SECRET = "a-long-secret-for-the-tests-0123456789"
LOGIN = {"email": "amara@example.com", "password": "demo-password"}

PROTECTED = [
    ("GET", "/payments", None),
    ("GET", "/payments/pay_1001", None),
    ("GET", "/sellers", None),
    ("GET", "/audit", None),
    ("GET", "/oath", None),
    ("PUT", "/oath", {"raw_text": "Spend up to $50 per job and $100 per day."}),
    ("POST", "/jobs", {"request_text": "Write a function."}),
    ("POST", "/jobs/job_2002/submission", {"seller_id": "sel_kip", "content": "x = 1"}),
    ("POST", "/payments/pay_1003/decision", {"decision": "approve"}),
    ("POST", "/demo/reset", None),
    ("POST", "/demo/attack/over_limit", None),
]


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
    app.dependency_overrides[get_session_factory] = lambda: factory
    app.dependency_overrides[get_demo_enabled] = lambda: True
    app.dependency_overrides[get_stream_settings] = lambda: StreamSettings(
        poll_seconds=0.05, ping_seconds=5.0, max_seconds=0.2
    )
    yield SimpleNamespace(client=TestClient(app), engine=engine)
    app.dependency_overrides.clear()


def login(api, body=None):
   return api.client.post("/auth/login", json=body if body is not None else LOGIN)


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


def token_for(api):
    return login(api).json()["access_token"]


def test_the_demo_user_can_log_in(api):
    response = login(api)
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["user"] == {
        "id": "usr_amara",
        "name": "Amara",
        "email": "amara@example.com",
        "role": "buyer",
        "seller_id": None,
    }
    assert read_token(body["access_token"]) == 1


def test_the_email_ignores_case_and_spaces(api):
    response = login(api, {"email": " Amara@Example.COM ", "password": "demo-password"})
    assert response.status_code == 200


def test_a_wrong_password_and_an_unknown_email_get_the_same_answer(api):
    wrong_password = login(api, {**LOGIN, "password": "nope"})
    unknown_email = login(api, {"email": "nobody@example.com", "password": "demo-password"})
    for response in (wrong_password, unknown_email):
        assert response.status_code == 401
        assert response.json()["error"] == {
            "code": "unauthorized",
            "message": "Wrong email or password.",
        }


def test_both_fields_are_required(api):
    for body in ({}, {"email": "amara@example.com"}, {**LOGIN, "password": ""}):
        response = login(api, body)
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "validation_error"


def test_the_password_is_stored_only_as_a_hash(api):
    with Session(api.engine) as db:
        stored = db.scalar(select(User)).password_hash
    assert stored.startswith("scrypt$")
    assert "demo-password" not in stored


def test_every_protected_endpoint_needs_a_token(api):
    for method, path, body in PROTECTED:
        response = api.client.request(method, path, json=body)
        assert response.status_code == 401, path
        assert response.json()["error"]["code"] == "unauthorized", path


def test_a_valid_token_opens_the_endpoints(api):
    headers = bearer(token_for(api))
    assert api.client.get("/payments", headers=headers).json()["total"] == 6
    assert api.client.get("/sellers", headers=headers).json()["total"] == 4
    assert api.client.get("/audit", headers=headers).json()["total"] == 12
    assert api.client.get("/oath", headers=headers).status_code == 200


def test_bad_tokens_are_refused_with_a_reason(api):
    def refused(headers):
        response = api.client.get("/payments", headers=headers)
        assert response.status_code == 401
        return response.json()["error"]["message"]

    assert refused(bearer("garbage")) == "Invalid token. Log in again."
    assert refused({"Authorization": "Basic abc"}) == "Log in to continue."
    long_ago = datetime.now(UTC) - timedelta(days=2)
    assert "expired" in refused(bearer(issue_token(1, now=long_ago)))
    assert "no longer exists" in refused(bearer(issue_token(999)))


def test_a_token_signed_with_another_secret_is_refused(api, monkeypatch):
    monkeypatch.setattr(settings, "jwt_secret", "some-other-secret-0123456789abcdef")
    foreign = issue_token(1)
    monkeypatch.setattr(settings, "jwt_secret", SECRET)
    response = api.client.get("/payments", headers=bearer(foreign))
    assert response.status_code == 401


def test_the_live_feed_takes_its_token_from_the_query_string(api):
    token = token_for(api)
    assert api.client.get("/events").status_code == 401
    assert api.client.get("/events?token=garbage").status_code == 401
    assert api.client.get("/events", headers=bearer(token)).status_code == 401
    good = api.client.get(f"/events?token={token}")
    assert good.status_code == 200
    assert good.headers["content-type"].startswith("text/event-stream")
    assert good.text.startswith(": connected")


def test_without_a_signing_secret_nothing_opens(api, monkeypatch):
    token = token_for(api)
    monkeypatch.setattr(settings, "jwt_secret", "")
    login_attempt = login(api)
    assert login_attempt.status_code == 500
    assert "JWT_SECRET" in login_attempt.json()["error"]["message"]
    assert api.client.get("/payments", headers=bearer(token)).status_code == 500


def test_the_health_check_stays_public(api):
    assert api.client.get("/health").status_code == 200


def test_the_seed_gives_an_older_database_a_login(api):
    with Session(api.engine) as db:
        db.scalar(select(User)).password_hash = None
        db.commit()
    assert login(api).status_code == 401
    with Session(api.engine) as db:
        assert seed_demo_data(db) == ["demo login"]
        db.commit()
    assert login(api).status_code == 200


def test_a_demo_reset_keeps_the_login_working(api):
    headers = bearer(token_for(api))
    assert api.client.post("/demo/reset", headers=headers).status_code == 204
    assert api.client.get("/payments", headers=headers).json()["total"] == 6
    assert login(api).status_code == 200
