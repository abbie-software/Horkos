from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, get_funder
from app.errors import ApiError
from app.models import Payment, PaymentState, User
from app.schemas.jobs import DecisionIn
from app.schemas.payments import PaymentList, PaymentOut, PaymentStatus
from app.services.funding import Funder
from app.services.jobs import confirm_funding, decide_payment
from app.services.views import load_payment_out

router = APIRouter(tags=["payments"])

DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]
FunderDep = Annotated[Funder, Depends(get_funder)]


def parse_payment_id(public_id: str) -> int | None:
    """Turn "pay_1003" into 1003. Anything else is not a payment ID."""
    prefix, _, number = public_id.partition("_")
    if prefix != "pay" or not number.isdigit():
        return None
    return int(number)


def find_payment(db: Session, user: User, public_id: str) -> Payment:
    number = parse_payment_id(public_id)
    payment = db.get(Payment, number) if number is not None else None
    if payment is None or payment.user_id != user.id:
        raise ApiError(404, "not_found", "Payment not found.")
    return payment


@router.get("/payments", response_model=PaymentList)
def list_payments(
    db: DbSession, user: CurrentUser, status: PaymentStatus | None = None
):
    query = (
        select(Payment)
        .where(Payment.user_id == user.id)
        .order_by(Payment.created_at.desc(), Payment.id.desc())
    )
    if status is not None:
        query = query.where(Payment.state == PaymentState(status))
    items = [load_payment_out(db, payment) for payment in db.scalars(query).all()]
    return PaymentList(items=items, total=len(items))


@router.get("/payments/{payment_id}", response_model=PaymentOut)
def read_payment(payment_id: str, db: DbSession, user: CurrentUser):
    return load_payment_out(db, find_payment(db, user, payment_id))


@router.post("/payments/{payment_id}/decision", response_model=PaymentOut)
def decide(
    payment_id: str,
    body: DecisionIn,
    db: DbSession,
    user: CurrentUser,
    funder: FunderDep,
):
    payment = find_payment(db, user, payment_id)
    decide_payment(db, payment, body.decision, funder)
    db.commit()
    return load_payment_out(db, payment)


@router.post("/payments/{payment_id}/funding/confirm", response_model=PaymentOut)
def confirm(payment_id: str, db: DbSession, user: CurrentUser, funder: FunderDep):
    """After the buyer approved the payment on PayPal: place the hold."""
    payment = find_payment(db, user, payment_id)
    confirm_funding(db, payment, funder)
    db.commit()
    return load_payment_out(db, payment)
