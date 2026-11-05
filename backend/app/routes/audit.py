from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import AuditEntry, Payment, User
from app.routes.payments import parse_payment_id
from app.schemas.activity import AuditList
from app.services.activity import audit_to_out

router = APIRouter(tags=["audit"])

DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.get("/audit", response_model=AuditList)
def list_audit(db: DbSession, user: CurrentUser, payment_id: str | None = None):
    """Every decision and settlement with its reason, newest first."""
    query = (
        select(AuditEntry)
        .join(Payment, Payment.id == AuditEntry.payment_id)
        .where(Payment.user_id == user.id)
    )
    if payment_id is not None:
        number = parse_payment_id(payment_id)
        if number is None:
            return AuditList(items=[], total=0)
        query = query.where(AuditEntry.payment_id == number)
    query = query.order_by(AuditEntry.created_at.desc(), AuditEntry.id.desc())
    items = [audit_to_out(entry) for entry in db.scalars(query).all()]
    return AuditList(items=items, total=len(items))
