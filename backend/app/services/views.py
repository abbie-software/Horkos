from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Payment, PaymentEvent, Seller
from app.schemas.payments import (
    SIGNAL_CODES,
    DecisionOut,
    PaymentOut,
    PaypalRefs,
    SignalOut,
    TransitionOut,
)
from app.schemas.sellers import SellerOut
from app.services.trust import tier_for
from app.timeutil import as_utc


def seller_public_id(seller: Seller) -> str:
    return seller.slug or f"sel_{seller.id}"


def seller_to_out(seller: Seller) -> SellerOut:
    last_activity = seller.last_activity_at
    return SellerOut(
        id=seller_public_id(seller),
        name=seller.name,
        paypal_email=seller.paypal_email,
        trust_score=seller.trust_score,
        tier=tier_for(seller.trust_score, seller.jobs_failed),
        limit_cents=seller.limit_cents,
        jobs_completed=seller.jobs_completed,
        jobs_failed=seller.jobs_failed,
        last_activity_at=as_utc(last_activity) if last_activity else None,
    )


def unchecked_decision() -> DecisionOut:
    """Shown when no Guard decision is stored. Fail safe: ask the user."""
    return DecisionOut(
        verdict="ask",
        risk_score=50,
        risk_level="medium",
        reason="No Guard decision has been recorded for this payment yet.",
        hard_rule=None,
        signals=[
            SignalOut(code=code, triggered=False, detail="Not checked.")
            for code in SIGNAL_CODES
        ],
    )


def payment_to_out(
    payment: Payment, seller: Seller, events: list[PaymentEvent]
) -> PaymentOut:
    decision = (
        DecisionOut.model_validate_json(payment.decision_json)
        if payment.decision_json
        else unchecked_decision()
    )
    return PaymentOut(
        id=f"pay_{payment.id}",
        job_id=f"job_{payment.job_id}" if payment.job_id else None,
        seller_id=seller_public_id(seller),
        seller_name=seller.name,
        amount_cents=payment.amount_cents,
        status=payment.state.value,
        decision=decision,
        history=[
            TransitionOut(status=e.to_state, at=as_utc(e.created_at), note=e.reason)
            for e in events
        ],
        paypal=PaypalRefs(
            funding_ref=payment.paypal_authorization_id or payment.paypal_order_id,
            payout_ref=payment.payout_ref,
            refund_ref=payment.refund_ref,
        ),
        created_at=as_utc(payment.created_at),
        updated_at=as_utc(payment.updated_at),
    )


def load_payment_out(db: Session, payment: Payment) -> PaymentOut:
    seller = db.get(Seller, payment.seller_id)
    events = db.scalars(
        select(PaymentEvent)
        .where(PaymentEvent.payment_id == payment.id)
        .order_by(PaymentEvent.id)
    ).all()
    return payment_to_out(payment, seller, list(events))