import json
import logging
from collections.abc import Callable
from dataclasses import asdict
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Job, Payment, PaymentEvent, PaymentState, Seller, Submission
from app.services.funding import Funder, SimulatedFunder
from app.services.ledger import transition
from app.services.sandbox import SandboxResult, run_in_sandbox
from app.services.trust import apply_outcome

log = logging.getLogger(__name__)


def payment_for_job(db: Session, job_id: int) -> Payment | None:
    return db.scalars(
        select(Payment).where(Payment.job_id == job_id).order_by(Payment.id.desc())
    ).first()


def sentence(text: str) -> str:
    text = text.strip()
    return text if text.endswith((".", "!", "?")) else text + "."


def refund_reason(result: SandboxResult) -> str:
    if result.total > 0:
        return f"{result.failed} of {result.total} tests failed."
    return sentence(result.output_excerpt)


def apply_verification(
    db: Session,
    submission_id: int,
    result: SandboxResult,
    funder: Funder,
    now: datetime,
) -> None:
    """Move the money and update the seller, once the work has been checked.

    The caller commits, so everything here is saved together or not at all.
    """
    submission = db.get(Submission, submission_id)
    job = db.get(Job, submission.job_id)
    seller = db.get(Seller, submission.seller_id)
    payment = payment_for_job(db, job.id)
    if payment is None or payment.state != PaymentState.HELD:
        raise RuntimeError("The payment is not being held, so it cannot be settled.")

    submission.result_json = json.dumps(asdict(result))

    if result.status == "error":
        # The runner could not reach a verdict. That says nothing about the
        # work, so nothing is paid or refunded and the seller can try again.
        submission.status = "error"
        job.status = "awaiting_work"
        db.add(
            PaymentEvent(
                payment_id=payment.id,
                from_state=payment.state.value,
                to_state=payment.state.value,
                reason=(
                    "Verification could not run, so nothing was paid or refunded. "
                    "The seller can submit again."
                ),
            )
        )
        return

    seller.last_activity_at = now
    if result.status == "passed":
        transition(
            db,
            payment,
            PaymentState.VERIFIED,
            f"{result.passed} of {result.total} tests passed.",
        )
        payment.payout_ref = funder.release(payment)
        old, new = apply_outcome(seller, passed=True)
        transition(
            db,
            payment,
            PaymentState.RELEASED,
            f"{seller.name} was paid. Trust score {old} to {new}.",
        )
        submission.status = "passed"
        job.status = "completed"
    else:
        old, new = apply_outcome(seller, passed=False)
        payment.refund_ref = funder.refund(payment)
        transition(
            db,
            payment,
            PaymentState.REFUNDED,
            f"{refund_reason(result)} You were refunded. Trust score {old} to {new}.",
        )
        submission.status = result.status
        job.status = "failed"


def put_back(session_factory: Callable[[], Session], submission_id: int) -> None:
    """After a crash, let the seller try again. The payment was never touched."""
    try:
        with session_factory() as db:
            submission = db.get(Submission, submission_id)
            if submission is not None:
                submission.status = "error"
                job = db.get(Job, submission.job_id)
                if job is not None and job.status == "verifying":
                    job.status = "awaiting_work"
            db.commit()
    except Exception:
        log.exception("Could not put the job back to waiting")


def verify_submission(
    session_factory: Callable[[], Session],
    submission_id: int,
    runner: Callable[[str, str], SandboxResult] = run_in_sandbox,
    funder: Funder | None = None,
    now: datetime | None = None,
) -> None:
    """Check the seller's work in the sandbox, then settle the payment.

    This runs in the background after the seller got their 202. The slow part,
    the sandbox, runs with no database transaction open.
    """
    funder = funder or SimulatedFunder()
    try:
        with session_factory() as db:
            submission = db.get(Submission, submission_id)
            job = db.get(Job, submission.job_id)
            content, test_code = submission.content, job.test_code or ""

        result = runner(content, test_code)

        with session_factory() as db:
            apply_verification(db, submission_id, result, funder, now or datetime.now(UTC))
            db.commit()
    except Exception:
        log.exception("Verification failed part-way")
        put_back(session_factory, submission_id)
