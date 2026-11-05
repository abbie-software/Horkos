import json

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import AuditEntry, Event, Payment, PaymentState, Seller
from app.schemas.activity import AuditOut, EventOut
from app.schemas.payments import DecisionOut
from app.services.hard_rules import dollars
from app.services.ledger import transition
from app.services.messages import (
    check_audit_reason,
    check_event_message,
    status_message,
    trust_audit_reason,
    trust_message,
    verdict_message,
)
from app.services.sandbox import SandboxResult
from app.services.views import seller_public_id
from app.timeutil import as_utc


def record_event(
    db: Session,
    kind: str,
    message: str,
    payload: dict,
    payment: Payment | None = None,
    seller: Seller | None = None,
) -> Event:
    event = Event(
        type=kind,
        message=message,
        payload_json=json.dumps(payload),
        payment_id=payment.id if payment is not None else None,
        seller_id=seller.id if seller is not None else None,
    )
    db.add(event)
    db.flush()
    return event


def record_audit(
    db: Session,
    payment: Payment,
    actor: str,
    action: str,
    reason: str,
    verdict: str | None = None,
    details: dict | None = None,
) -> AuditEntry:
    entry = AuditEntry(
        payment_id=payment.id,
        actor=actor,
        action=action,
        verdict=verdict,
        reason=reason,
        details_json=json.dumps(details or {}),
    )
    db.add(entry)
    db.flush()
    return entry


def record_proposal(db: Session, payment: Payment, seller: Seller) -> None:
    amount = dollars(payment.amount_cents)
    record_event(
        db,
        "payment.proposed",
        f"Buyer Agent proposed paying {amount} to {seller.name}.",
        {"amount_cents": payment.amount_cents},
        payment,
        seller,
    )
    record_audit(
        db,
        payment,
        "buyer_agent",
        "Proposed a payment",
        f"Proposed {amount} to {seller.name}.",
        details={"amount_cents": payment.amount_cents},
    )


def record_verdict(
    db: Session, payment: Payment, seller: Seller, decision: DecisionOut
) -> None:
    payload = {
        "verdict": decision.verdict,
        "risk_level": decision.risk_level,
        "risk_score": decision.risk_score,
    }
    details = {"risk_score": decision.risk_score}
    if decision.hard_rule:
        payload["hard_rule"] = decision.hard_rule
        details["hard_rule"] = decision.hard_rule
    record_event(db, "payment.verdict", verdict_message(decision), payload, payment, seller)
    record_audit(
        db,
        payment,
        "guard",
        "Reviewed the payment",
        decision.reason,
        verdict=decision.verdict,
        details=details,
    )


def move(
    db: Session,
    payment: Payment,
    seller: Seller,
    new_state: PaymentState,
    reason: str,
) -> None:
    """Move a payment to a new state and tell the Live Feed and the audit trail."""
    before = payment.state
    transition(db, payment, new_state, reason)
    record_event(
        db,
        "payment.status_changed",
        status_message(new_state.value, seller.name, payment.amount_cents),
        {"from": before.value, "to": new_state.value},
        payment,
        seller,
    )
    amount = dollars(payment.amount_cents)
    if new_state == PaymentState.HELD:
        record_audit(
            db,
            payment,
            "system",
            "Secured funds",
            "Funds secured in escrow.",
            details={"funding_ref": payment.paypal_authorization_id},
        )
    elif new_state == PaymentState.RELEASED:
        record_audit(
            db, payment, "system", "Released payment", f"{seller.name} was paid {amount}."
        )
    elif new_state == PaymentState.REFUNDED:
        record_audit(
            db, payment, "system", "Refunded the buyer", "The payment was refunded to the buyer."
        )


def record_user_choice(db: Session, payment: Payment, approved: bool) -> None:
    record_audit(
        db,
        payment,
        "user",
        "Approved the payment" if approved else "Rejected the payment",
        "You approved the payment." if approved else "You rejected the payment.",
    )


def record_check(
    db: Session, payment: Payment, seller: Seller, result: SandboxResult
) -> None:
    """The sandbox's verdict on the seller's work."""
    if result.status == "error":
        record_audit(
            db,
            payment,
            "system",
            "Could not check the work",
            "The test runner could not reach a verdict, so nothing was paid or refunded.",
        )
        return
    record_event(
        db,
        "verification.result",
        check_event_message(result),
        {
            "passed": result.status == "passed",
            "tests_passed": result.passed,
            "tests_total": result.total,
        },
        payment,
        seller,
    )
    record_audit(
        db,
        payment,
        "verifier",
        "Checked the work",
        check_audit_reason(result),
        details={"passed": result.passed, "total": result.total},
    )


def record_trust(
    db: Session, payment: Payment, seller: Seller, old: int, new: int
) -> None:
    if new == old:
        return
    record_event(
        db,
        "trust.updated",
        trust_message(seller.name, old, new, seller.limit_cents),
        {"old_score": old, "new_score": new, "new_limit_cents": seller.limit_cents},
        payment,
        seller,
    )
    record_audit(
        db,
        payment,
        "system",
        "Raised trust" if new > old else "Lowered trust",
        trust_audit_reason(seller.name, old, new, seller.limit_cents),
        details={"old_score": old, "new_score": new},
    )


# --- reading ---------------------------------------------------------------


def audit_to_out(entry: AuditEntry) -> AuditOut:
    return AuditOut(
        id=f"aud_{entry.id:03d}",
        payment_id=f"pay_{entry.payment_id}",
        at=as_utc(entry.created_at),
        actor=entry.actor,
        action=entry.action,
        verdict=entry.verdict,
        reason=entry.reason,
        details=json.loads(entry.details_json),
    )


def seller_slugs(db: Session) -> dict[int, str]:
    return {s.id: seller_public_id(s) for s in db.scalars(select(Seller)).all()}


def event_to_out(event: Event, slugs: dict[int, str]) -> EventOut:
    return EventOut(
        id=f"evt_{event.id:03d}",
        type=event.type,
        at=as_utc(event.created_at),
        payment_id=f"pay_{event.payment_id}" if event.payment_id else None,
        seller_id=slugs.get(event.seller_id) if event.seller_id else None,
        message=event.message,
        payload=json.loads(event.payload_json),
    )


def latest_event_id(factory) -> int:
    with factory() as db:
        return db.scalar(select(func.max(Event.id))) or 0


def read_events_after(factory, after_id: int, limit: int = 100) -> list[tuple[int, str]]:
    """New events as (number, JSON) pairs, oldest first."""
    with factory() as db:
        rows = db.scalars(
            select(Event).where(Event.id > after_id).order_by(Event.id).limit(limit)
        ).all()
        slugs = seller_slugs(db)
        return [(e.id, event_to_out(e, slugs).model_dump_json()) for e in rows]
