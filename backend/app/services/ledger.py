from sqlalchemy.orm import Session

from app.models import Payment, PaymentEvent, PaymentState

S = PaymentState

ALLOWED_TRANSITIONS: dict[PaymentState, set[PaymentState]] = {
    S.PROPOSED: {S.APPROVED, S.BLOCKED},
    S.APPROVED: {S.HELD, S.BLOCKED},
    S.HELD: {S.VERIFIED, S.REFUNDED},
    S.VERIFIED: {S.RELEASED},
    S.RELEASED: set(),
    S.REFUNDED: set(),
    S.BLOCKED: set(),
}


class InvalidTransition(Exception):
    """Raised when a payment is asked to move in a way the rules do not allow."""


def create_payment(
    db: Session,
    *,
    user_id: int,
    seller_id: int,
    amount_cents: int,
    description: str,
) -> Payment:
    if (
        not isinstance(amount_cents, int)
        or isinstance(amount_cents, bool)
        or amount_cents <= 0
    ):
        raise ValueError("amount_cents must be a positive whole number of cents")

    payment = Payment(
        user_id=user_id,
        seller_id=seller_id,
        amount_cents=amount_cents,
        description=description,
        state=S.PROPOSED,
    )
    db.add(payment)
    db.flush()
    db.add(
        PaymentEvent(
            payment_id=payment.id,
            from_state=None,
            to_state=S.PROPOSED.value,
            reason="Payment proposed",
        )
    )
    db.flush()
    return payment


def transition(
    db: Session, payment: Payment, new_state: PaymentState, reason: str
) -> Payment:
    if not reason or not reason.strip():
        raise ValueError("A reason is required for every state change")

    current = payment.state
    if new_state not in ALLOWED_TRANSITIONS[current]:
        raise InvalidTransition(
            f"A payment cannot move from {current.value} to {new_state.value}."
        )

    payment.state = new_state
    db.add(
        PaymentEvent(
            payment_id=payment.id,
            from_state=current.value,
            to_state=new_state.value,
            reason=reason.strip(),
        )
    )
    db.flush()
    return payment