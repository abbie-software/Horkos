from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.deps import get_demo_enabled, get_session_factory
from app.main import app
from app.models import Seller, User
from app.scripts.seed import seed_demo_data
from app.services.demo import CLEARED_IN_ORDER

# These tests use the real login check, not the demo-user shortcut.
pytestmark = pytest.mark.real_auth

SECRET = "a-long-secret-for-the-tests-0123456789"
PASSWORD = "demo-password"


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
    yield SimpleNamespace(client=TestClient(app), engine=engine)
    app.dependency_overrides.clear()


def log_in(api, email):
    return api.client.post("/auth/login", json={"email": email, "password": PASSWORD})


def headers_for(api, email):
    return {"Authorization": f"Bearer {log_in(api, email).json()['access_token']}"}


def job_ids(response):
    assert response.status_code == 200
    return {item["id"] for item in response.json()["items"]}


def test_a_seller_account_says_who_it_is(api):
    user = log_in(api, "kip@example.com").json()["user"]
    assert user["role"] == "seller"
    assert user["seller_id"] == "sel_kip"
    assert user["name"] == "Kip Codes"


def test_every_demo_seller_can_log_in(api):
    for email, seller in [
        ("nova@example.com", "sel_nova"),
        ("kip@example.com", "sel_kip"),
        ("zed@example.com", "sel_zed"),
        ("quick@example.com", "sel_quick"),
    ]:
        assert log_in(api, email).json()["user"]["seller_id"] == seller


def test_the_buyer_account_has_no_seller(api):
    user = log_in(api, "amara@example.com").json()["user"]
    assert user["role"] == "buyer"
    assert user["seller_id"] is None


def test_a_seller_sees_only_their_own_jobs(api):
    kip = headers_for(api, "kip@example.com")
    nova = headers_for(api, "nova@example.com")
    assert job_ids(api.client.get("/jobs", headers=kip)) == {"job_2002"}
    assert job_ids(api.client.get("/jobs", headers=nova)) == {"job_2001", "job_2005"}


def test_the_status_filter_narrows_the_list(api):
    kip = headers_for(api, "kip@example.com")
    nova = headers_for(api, "nova@example.com")
    assert job_ids(api.client.get("/jobs?status=awaiting_work", headers=kip)) == {"job_2002"}
    assert job_ids(api.client.get("/jobs?status=completed", headers=kip)) == set()
    assert job_ids(api.client.get("/jobs?status=awaiting_work", headers=nova)) == set()


def test_a_seller_cannot_ask_for_someone_elses_jobs(api):
    kip = headers_for(api, "kip@example.com")
    assert job_ids(api.client.get("/jobs?seller_id=sel_nova", headers=kip)) == set()


def test_a_buyer_sees_their_jobs_and_can_filter_by_seller(api):
    amara = headers_for(api, "amara@example.com")
    assert len(job_ids(api.client.get("/jobs", headers=amara))) == 6
    found = api.client.get("/jobs?status=awaiting_work&seller_id=sel_kip", headers=amara)
    assert job_ids(found) == {"job_2002"}


def test_the_job_list_never_shows_the_tests_code(api):
    kip = headers_for(api, "kip@example.com")
    item = api.client.get("/jobs", headers=kip).json()["items"][0]
    assert "test_code" not in item
    assert item["acceptance_tests"]


def test_the_job_list_needs_a_login(api):
    response = api.client.get("/jobs")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_a_seller_cannot_submit_work_to_another_sellers_job(api):
    zed = headers_for(api, "zed@example.com")
    response = api.client.post(
        "/jobs/job_2002/submission",
        headers=zed,
        json={"seller_id": "sel_kip", "content": "x = 1"},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_the_demo_reset_keeps_the_seller_logins(api):
    amara = headers_for(api, "amara@example.com")
    assert api.client.post("/demo/reset", headers=amara).status_code == 204
    assert log_in(api, "kip@example.com").json()["user"]["seller_id"] == "sel_kip"


def test_the_reset_clears_users_before_sellers():
    assert CLEARED_IN_ORDER.index(User) < CLEARED_IN_ORDER.index(Seller)


def test_a_job_shows_the_amount_to_be_paid(api):
    kip = headers_for(api, "kip@example.com")
    amara = headers_for(api, "amara@example.com")
    item = api.client.get("/jobs", headers=kip).json()["items"][0]
    payment = api.client.get(f"/payments/{item['payment_id']}", headers=amara).json()
    assert item["amount_cents"] == payment["amount_cents"] > 0