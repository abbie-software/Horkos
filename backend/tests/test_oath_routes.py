import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import User

DEMO_OATH = (
    "Spend up to $50 per job and $100 per day. Only on coding work. "
    "Ask me before anything over $30, and always ask me about a seller "
    "I have not used before."
)
CONTRACT_POLICY = {
    "per_job_cap_cents": 5000,
    "daily_cap_cents": 10000,
    "ask_threshold_cents": 3000,
    "allowed_categories": ["coding"],
    "blocked_categories": [],
    "ask_for_new_sellers": True,
}


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(User(email="amara@example.com", name="Amara"))
        session.commit()

    def override_get_db():
        with Session(engine, expire_on_commit=False) as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_get_before_any_save_is_a_contract_shaped_404(client):
    response = client.get("/oath")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_saved_oath_comes_back_on_the_next_call(client):
    saved = client.put("/oath", json={"raw_text": DEMO_OATH})
    assert saved.status_code == 200
    body = saved.json()
    assert set(body) == {"id", "raw_text", "policy", "updated_at"}
    assert body["policy"] == CONTRACT_POLICY
    assert body["id"].startswith("oath_")

    loaded = client.get("/oath")
    assert loaded.status_code == 200
    assert loaded.json() == body


def test_a_second_save_replaces_the_first(client):
    client.put("/oath", json={"raw_text": DEMO_OATH})
    client.put("/oath", json={"raw_text": "Spend up to $20 per job and $40 per day."})
    body = client.get("/oath").json()
    assert body["policy"]["per_job_cap_cents"] == 2000


def test_an_oath_missing_a_limit_is_rejected_and_not_saved(client):
    response = client.put("/oath", json={"raw_text": "Spend up to $50 per job."})
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "validation_error"
    assert "each day" in error["message"]
    assert client.get("/oath").status_code == 404


def test_a_request_without_raw_text_uses_the_contract_error_shape(client):
    response = client.put("/oath", json={})
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "validation_error"
    assert "raw_text" in error["message"]


def test_an_unknown_route_uses_the_contract_error_shape(client):
    response = client.get("/nope")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"