import shutil
import subprocess
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.deps import (
    get_buyer_agent,
    get_funder,
    get_intent_checker,
    get_runner,
    get_session_factory,
)
from app.main import app
from app.models import Job, Submission
from app.scripts.seed import seed_demo_data
from app.services.buyer_agent import BuyerProposal
from app.services.funding import SimulatedFunder
from app.services.sandbox import IMAGE, SandboxResult, run_in_sandbox
from app.services.signals import IntentResult

TEST_CODE = (
    "from solution import double\n"
    "\n"
    "def test_doubles_a_number():\n"
    "    assert double(2) == 4\n"
)
GOOD_CODE = 'def reverse_words(sentence):\n    return " ".join(reversed(sentence.split()))\n'
BAD_CODE = "def reverse_words(sentence):\n    return sentence\n"

PASSED = SandboxResult(
    status="passed", passed=3, total=3, duration_ms=12, output_excerpt="3 passed in 0.01s"
)
FAILED = SandboxResult(
    status="failed", passed=1, failed=2, total=3, duration_ms=12,
    output_excerpt="2 failed, 1 passed.",
)
TIMED_OUT = SandboxResult(
    status="timeout",
    output_excerpt="The code ran for longer than 10 seconds and was stopped.",
)
COULD_NOT_RUN = SandboxResult(status="error", output_excerpt="Docker is not installed.")


class FakeAgent:
    def propose(self, request_text):
        return BuyerProposal(
            category="coding",
            amount_cents=2000,
            description="A small Python function.",
            acceptance_tests=["Define double(n) that returns n times two"],
            test_code=TEST_CODE,
        )


class FakeChecker:
    def check(self, request_text, payment_summary):
        return IntentResult(mismatch=False, detail="")


class FakeRunner:
    def __init__(self, result):
        self.result, self.calls = result, []

    def __call__(self, content, test_code):
        self.calls.append((content, test_code))
        if isinstance(self.result, Exception):
            raise self.result
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


def install(engine, runner):
    factory = sessionmaker(bind=engine, expire_on_commit=False)

    def override_get_db():
        with factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_session_factory] = lambda: factory
    app.dependency_overrides[get_runner] = lambda: runner
    app.dependency_overrides[get_buyer_agent] = lambda: FakeAgent()
    app.dependency_overrides[get_intent_checker] = lambda: FakeChecker()
    app.dependency_overrides[get_funder] = lambda: SimulatedFunder()
    return TestClient(app)


@pytest.fixture()
def shop():
    engine = make_engine()
    runner = FakeRunner(PASSED)
    client = install(engine, runner)
    yield SimpleNamespace(client=client, engine=engine, runner=runner)
    app.dependency_overrides.clear()


@pytest.fixture()
def real_shop():
    engine = make_engine()
    client = install(engine, run_in_sandbox)
    yield SimpleNamespace(client=client, engine=engine)
    app.dependency_overrides.clear()


def submit(shop, job="job_2002", seller="sel_kip", content=GOOD_CODE):
    return shop.client.post(
        f"/jobs/{job}/submission", json={"seller_id": seller, "content": content}
    )


def payment(shop, number=1002):
    return shop.client.get(f"/payments/pay_{number}").json()


def seller_info(shop, slug):
    items = shop.client.get("/sellers").json()["items"]
    return next(s for s in items if s["id"] == slug)


def stored(shop, model, number, attribute):
    with Session(shop.engine) as db:
        return getattr(db.get(model, number), attribute)


def test_good_work_is_verified_and_the_seller_is_paid(shop):
    response = submit(shop)
    assert response.status_code == 202
    assert response.json() == {
        "submission_id": "sub_1",
        "status": "verifying",
        "payment_id": "pay_1002",
    }

    result = payment(shop)
    assert result["status"] == "released"
    assert [h["status"] for h in result["history"]][-2:] == ["verified", "released"]
    assert result["history"][-2]["note"] == "3 of 3 tests passed."
    assert result["history"][-1]["note"] == "Kip Codes was paid. Trust score 46 to 58."
    assert result["paypal"]["payout_ref"] == "SIM-PAYOUT-1002"

    kip = seller_info(shop, "sel_kip")
    assert (kip["trust_score"], kip["jobs_completed"]) == (58, 3)
    assert (kip["tier"], kip["limit_cents"]) == ("building", 2500)
    assert stored(shop, Job, 2002, "status") == "completed"
    assert stored(shop, Submission, 1, "status") == "passed"

    code, tests = shop.runner.calls[0]
    assert code == GOOD_CODE
    assert "reverse_words" in tests


def test_failed_work_refunds_the_buyer_and_cuts_the_sellers_trust(shop):
    shop.runner.result = FAILED
    assert submit(shop).status_code == 202

    result = payment(shop)
    assert result["status"] == "refunded"
    assert result["history"][-1]["note"] == (
        "2 of 3 tests failed. You were refunded. Trust score 46 to 24."
    )
    assert result["paypal"]["refund_ref"] == "SIM-REFUND-1002"
    assert result["paypal"]["payout_ref"] is None

    kip = seller_info(shop, "sel_kip")
    assert (kip["trust_score"], kip["jobs_failed"]) == (24, 1)
    assert (kip["tier"], kip["limit_cents"]) == ("restricted", 500)
    assert stored(shop, Job, 2002, "status") == "failed"
    assert stored(shop, Submission, 1, "status") == "failed"


def test_code_that_runs_too_long_is_refunded_too(shop):
    shop.runner.result = TIMED_OUT
    submit(shop)
    result = payment(shop)
    assert result["status"] == "refunded"
    assert result["history"][-1]["note"].startswith(
        "The code ran for longer than 10 seconds and was stopped. You were refunded."
    )
    assert stored(shop, Submission, 1, "status") == "timeout"


def test_when_the_runner_cannot_decide_nothing_is_paid_or_refunded(shop):
    shop.runner.result = COULD_NOT_RUN
    assert submit(shop).status_code == 202

    result = payment(shop)
    assert result["status"] == "held"
    assert result["history"][-1]["note"].startswith("Verification could not run")
    assert seller_info(shop, "sel_kip")["trust_score"] == 46
    assert stored(shop, Job, 2002, "status") == "awaiting_work"
    assert stored(shop, Submission, 1, "status") == "error"

    shop.runner.result = PASSED  # the seller can try again
    assert submit(shop).status_code == 202
    assert payment(shop)["status"] == "released"


def test_a_crash_while_verifying_puts_the_job_back_and_keeps_the_money_held(shop):
    shop.runner.result = RuntimeError("the sandbox exploded")
    assert submit(shop).status_code == 202
    assert payment(shop)["status"] == "held"
    assert stored(shop, Job, 2002, "status") == "awaiting_work"
    assert stored(shop, Submission, 1, "status") == "error"


def test_a_job_can_only_be_submitted_to_once_while_it_is_being_settled(shop):
    assert submit(shop).status_code == 202
    again = submit(shop)
    assert again.status_code == 409
    assert again.json()["error"] == {
        "code": "invalid_state",
        "message": "This job is not waiting for work.",
    }
    assert len(shop.runner.calls) == 1


def test_only_the_jobs_own_seller_can_submit(shop):
    response = submit(shop, seller="sel_nova")
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert shop.runner.calls == []


def test_unknown_jobs_and_jobs_not_waiting_for_work_are_refused(shop):
    missing = submit(shop, job="job_9999")
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "not_found"
    assert submit(shop, job="banana").status_code == 404

    waiting_for_the_user = submit(shop, job="job_2003", seller="sel_zed")
    assert waiting_for_the_user.status_code == 409
    assert waiting_for_the_user.json()["error"]["code"] == "invalid_state"
    assert shop.runner.calls == []


def test_blank_work_is_refused(shop):
    for content in ("", "   "):
        response = submit(shop, content=content)
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "validation_error"
    assert shop.runner.calls == []


def test_a_job_without_tests_cannot_be_checked(shop):
    with Session(shop.engine) as db:
        db.get(Job, 2002).test_code = None
        db.commit()
    response = submit(shop)
    assert response.status_code == 409
    assert "no tests" in response.json()["error"]["message"]


def test_a_new_job_carries_its_tests_through_to_verification(shop):
    created = shop.client.post(
        "/jobs", json={"request_text": "Write a function that doubles a number."}
    )
    assert created.status_code == 201
    job = created.json()["job"]
    assert job["seller_id"] == "sel_nova"

    response = submit(
        shop, job=job["id"], seller="sel_nova", content="def double(n):\n    return n * 2\n"
    )
    assert response.status_code == 202
    assert shop.runner.calls[0][1] == TEST_CODE
    assert payment(shop, 1007)["status"] == "released"
    assert seller_info(shop, "sel_nova")["trust_score"] == 94


# --- the whole thing with the real sandbox ---------------------------------


def docker_ready() -> bool:
    if shutil.which("docker") is None:
        return False
    try:
        check = subprocess.run(
            ["docker", "image", "inspect", IMAGE],
            capture_output=True,
            timeout=20,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return check.returncode == 0


needs_docker = pytest.mark.skipif(
    not docker_ready(), reason=f"Docker is not running or {IMAGE} is not pulled"
)


@needs_docker
def test_real_sandbox_good_work_is_paid(real_shop):
    assert submit(real_shop).status_code == 202
    assert payment(real_shop)["status"] == "released"


@needs_docker
def test_real_sandbox_wrong_work_is_refunded(real_shop):
    assert submit(real_shop, content=BAD_CODE).status_code == 202
    result = payment(real_shop)
    assert result["status"] == "refunded"
    assert result["history"][-1]["note"].startswith("1 of 3 tests failed.")
