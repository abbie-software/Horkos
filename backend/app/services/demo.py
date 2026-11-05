from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from app.models import (
    AuditEntry,
    Event,
    Job,
    Oath,
    Payment,
    PaymentEvent,
    Seller,
    Submission,
    User,
)
from app.scripts.seed import seed_demo_data

# Children first, so nothing is deleted while something still points at it.
CLEARED_IN_ORDER = [AuditEntry, Submission, PaymentEvent, Payment, Job, Oath, User, Seller]


def attacks_so_far(db: Session) -> int:
    return db.scalar(
        select(func.count()).select_from(Event).where(Event.type == "demo.attack_started")
    ) or 0


def reset_demo_data(db: Session) -> None:
    """Put the demo data back to its starting point.

    Old events are kept, so the numbers in the Live Feed keep counting up and a
    connected screen never misses the reset. They just stop pointing at
    payments and sellers that no longer exist.
    """
    db.execute(update(Event).values(payment_id=None, seller_id=None))
    for model in CLEARED_IN_ORDER:
        db.execute(delete(model))
    db.flush()
    seed_demo_data(db)
