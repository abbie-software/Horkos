import json
import logging
from datetime import UTC, datetime, timedelta
from typing import Literal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.errors import ApiError
from app.models import Job, Payment, PaymentState, Seller, User
from app.schemas.oath import Policy
from app.schemas.payments import DecisionOut
from app.services.activity import (
    move,
    record_audit,
    record_proposal,
    record_user_choice,
    record_verdict,
)
from app.services.buyer_agent import BuyerAgent, BuyerAgentError
from app.services.funding import Funder, FundingError, NotApprovedYet
from app.services.guard import IntentChecker, safe_review
from app.services.hard_rules import Proposal, SellerFacts, dollars
from app.services.ledger import create_payment
from app.services.messages import BLOCK_NOTES
from app.services.oath_store import get_latest_oath
from app.services.seller_choice import pick_seller
from app.services.signals import Activity

log = logging.getLogger(__name__)

VELOCITY_WINDOW_MINUTES = 10

# Money counts as spent today once a payment is approved, and stays counted
# until it is refunded or blocked.
COUNTED_AS_SPENT = (
    PaymentState.APPROVED,
    PaymentState.HELD,
    PaymentState.VERIFIED,
    PaymentState.RELEASED,
)


def seller_facts(seller: Seller) -> SellerFacts:
    return SellerFacts(
        name=seller.name,
        agreed_email=seller.paypal_email,
        trust_score=seller.trust_score,
        jobs_failed=seller.jobs_failed,
        limit_cents=seller.limit_cents,
        jobs_completed=seller.jobs_completed,
    )


def load_activity(
    db: Session, user_id: int, now: datetime, exclude_payment_id: int | None = None
) -> Activity:
    """What this user has been doing lately, for the daily cap and the velocity signal."""
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    window_start = now - timedelta(minutes=VELOCITY_WINDOW_MINUTES)

    def mine(query):
        query = query.where(Payment.user_id == user_id)
        if exclude_payment_id is not None:
            query = query.where(Payment.id != exclude_payment_id)
        return query

    spent = db.scalar(
        mine(select(func.coalesce(func.sum(Payment.amount_cents), 0))).where(
            Payment.created_at >= start_of_day,
            Payment.state.in_(COUNTED_AS_SPENT),
        )
    )
    proposals = db.scalar(
        mine(select(func.count()).select_from(Payment)).where(
            Payment.created_at >= window_start
        )
    )
    blocks = db.scalar(
        mine(select(func.count()).select_from(Payment)).where(
            Payment.created_at >= window_start,
            Payment.state == PaymentState.BLOCKED,
        )
    )
    return Activity(
        spent_today_cents=int(spent or 0),
        recent_proposals=int(proposals or 0),
        recent_blocks=int(blocks or 0),
    )


def block_note(decision: DecisionOut) -> str:
    if decision.hard_rule:
        return f"Guard blocked: {BLOCK_NOTES[decision.hard_rule]}"
    return f"Guard blocked: the risk score is {decision.risk_score} out of 100."


def begin_funding(
    db: Session, payment: Payment, job: Job | None, seller: Seller, funder: Funder
) -> None:
    """Start securing the buyer's money for an approved payment.

    A simulated funder holds it straight away. The PayPal funder cannot: the
    buyer has to approve it on PayPal first, so the payment waits in the
    approved state with a link for the buyer.
    """
    try:
        start = funder.start(payment, seller)
    except FundingError as exc:
        log.exception("Funding could not start")
        raise ApiError(
            500, "server_error", "PayPal could not start this payment. Please try again."
        ) from exc

    if start.held:
        payment.paypal_authorization_id = start.ref
        move(db, payment, seller, PaymentState.HELD, "Funds secured.")
        if job is not None:
            job.status = "awaiting_work"
        return

    payment.paypal_order_id = start.ref
    payment.approve_url = start.approve_url
    record_audit(
        db,
        payment,
        "system",
        "Asked the buyer to fund the payment",
        "Waiting for the buyer to approve the payment on PayPal.",
        details={"order_id": start.ref},
    )


def confirm_funding(db: Session, payment: Payment, funder: Funder) -> Payment:
    """The buyer approved on PayPal: place the hold and start the job."""
    if payment.state != PaymentState.APPROVED or not payment.paypal_order_id:
        raise ApiError(409, "invalid_state", "This payment is not waiting for funding.")

    try:
        authorization = funder.confirm(payment)
    except NotApprovedYet as exc:
        raise ApiError(
            422, "validation_error", "The buyer has not approved this payment on PayPal yet."
        ) from exc
    except FundingError as exc:
        log.exception("Funding could not be confirmed")
        raise ApiError(
            500, "server_error", "PayPal could not secure the funds. Please try again."
        ) from exc

    seller = db.get(Seller, payment.seller_id)
    job = db.get(Job, payment.job_id) if payment.job_id else None
    payment.paypal_authorization_id = authorization
    payment.approve_url = None
    move(db, payment, seller, PaymentState.HELD, "Funds secured.")
    if job is not None:
        job.status = "awaiting_work"
    return payment


def apply_verdict(
    db: Session,
    payment: Payment,
    job: Job,
    seller: Seller,
    decision: DecisionOut,
    funder: Funder,
) -> None:
    if decision.verdict == "block":
        move(db, payment, seller, PaymentState.BLOCKED, block_note(decision))
        job.status = "cancelled"
    elif decision.verdict == "ask":
        move(
            db,
            payment,
            seller,
            PaymentState.AWAITING_USER,
            "Guard asked the user to decide.",
        )
    else:
        move(
            db,
            payment,
            seller,
            PaymentState.APPROVED,
            f"Guard approved ({decision.risk_level} risk).",
        )
        begin_funding(db, payment, job, seller, funder)


def run_job(
    db: Session,
    user: User,
    request_text: str,
    seller_ref: str | None,
    agent: BuyerAgent,
    checker: IntentChecker,
    funder: Funder,
    now: datetime | None = None,
    recipient_email: str | None = None,
) -> tuple[Job, Payment]:
    """Start a job: the Buyer Agent proposes a payment and the Guard decides.

    Nothing is committed here. The caller commits once, so a failure part-way
    through leaves nothing behind. recipient_email is only used by the demo's
    Red Team, to play a payment that tries to go to a different account.
    """
    now = now or datetime.now(UTC)

    oath = get_latest_oath(db, user.id)
    if oath is None:
        raise ApiError(409, "invalid_state", "Save your oath before starting a job.")
    policy = Policy.model_validate_json(oath.policy_json)

    seller = None
    if seller_ref:
        seller = db.scalar(select(Seller).where(Seller.slug == seller_ref))
        if seller is None:
            raise ApiError(404, "not_found", "Seller not found.")

    try:
        idea = agent.propose(request_text)
    except BuyerAgentError as exc:
        raise ApiError(500, "server_error", str(exc)) from exc

    if seller is None:
        sellers = db.scalars(select(Seller).order_by(Seller.id)).all()
        if not sellers:
            raise ApiError(404, "not_found", "No sellers are available.")
        seller = pick_seller(sellers, idea.amount_cents)

    job = Job(
        user_id=user.id,
        seller_id=seller.id,
        request_text=request_text,
        category=idea.category,
        status="open",
        acceptance_tests_json=json.dumps(idea.acceptance_tests),
        test_code=idea.test_code,
    )
    db.add(job)
    db.flush()

    payment = create_payment(
        db,
        user_id=user.id,
        seller_id=seller.id,
        amount_cents=idea.amount_cents,
        description=idea.description,
        job_id=job.id,
        reason=(
            f"Buyer Agent proposed paying {dollars(idea.amount_cents)} to {seller.name}."
        ),
    )
    record_proposal(db, payment, seller)

    activity = load_activity(db, user.id, now, exclude_payment_id=payment.id)
    proposal = Proposal(
        amount_cents=idea.amount_cents,
        category=idea.category,
        recipient_email=recipient_email or seller.paypal_email,
        description=idea.description,
    )
    decision = safe_review(
        proposal, seller_facts(seller), policy, request_text, activity, checker
    )
    payment.decision_json = decision.model_dump_json()
    record_verdict(db, payment, seller, decision)
    apply_verdict(db, payment, job, seller, decision, funder)
    return job, payment


def decide_payment(
    db: Session,
    payment: Payment,
    choice: Literal["approve", "reject"],
    funder: Funder,
) -> Payment:
    """The user's answer to an Ask."""
    if payment.state != PaymentState.AWAITING_USER:
        raise ApiError(409, "invalid_state", "This payment has already been decided.")

    job = db.get(Job, payment.job_id) if payment.job_id else None
    seller = db.get(Seller, payment.seller_id)
    approved = choice == "approve"
    record_user_choice(db, payment, approved)
    if approved:
        move(db, payment, seller, PaymentState.APPROVED, "You approved the payment.")
        begin_funding(db, payment, job, seller, funder)
    else:
        move(db, payment, seller, PaymentState.BLOCKED, "You rejected the payment.")
        if job is not None:
            job.status = "cancelled"
    return payment
