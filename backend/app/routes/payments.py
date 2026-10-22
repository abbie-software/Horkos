from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.errors import ApiError
from app.models import Payment, PaymentState, User
from app.schemas.payments import PaymentList, PaymentOut, PaymentStatus
from app.services.views import load_payment_out

router = APIRouter(tags=["payments"])

DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


def parse_payment_id(public_id: str) -> int | None:
    """Turn "pay_1003" into 1003. Anything else is not a payment ID."""
    prefix, _, number = public_id.partition("_")
    if prefix != "pay" or not number.isdigit():
        return None
    return int(number)


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
    number = parse_payment_id(payment_id)
    payment = db.get(Payment, number) if number is not None else None
    if payment is None or payment.user_id != user.id:
        raise ApiError(404, "not_found", "Payment not found.")
    return load_payment_out(db, payment)