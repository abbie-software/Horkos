import json
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import (
    AuditEntry,
    Job,
    Payment,
    PaymentEvent,
    PaymentState,
    Seller,
    User,
)
from app.scripts.demo_data import (
    AUDIT,
    DEMO_OATH,
    DEMO_USER,
    JOBS,
    PAYMENTS,
    SELLERS,
)
from app.services.oath_store import get_latest_oath, save_oath


def ts(value: str) -> datetime:
    return datetime.fromisoformat(value)


def seed_demo_data(db: Session) -> list[str]:
    """Add whatever demo data is missing. Safe to run more than once."""
    added: list[str] = []

    user = db.scalar(select(User).where(User.email == DEMO_USER["email"]))
    if user is None:
        user = User(**DEMO_USER)
        db.add(user)
        db.flush()
        added.append("demo user Amara")

    if get_latest_oath(db, user.id) is None:
        save_oath(db, user.id, DEMO_OATH)
        added.append("demo oath")

    sellers: dict[str, Seller] = {}
    for data in SELLERS:
        seller = db.scalar(select(Seller).where(Seller.slug == data["slug"]))
        if seller is None:
            last_activity = data["last_activity_at"]
            seller = Seller(
                slug=data["slug"],
                name=data["name"],
                paypal_email=data["paypal_email"],
                trust_score=data["trust_score"],
                limit_cents=data["limit_cents"],
                jobs_completed=data["jobs_completed"],
                jobs_failed=data["jobs_failed"],
                last_activity_at=ts(last_activity) if last_activity else None,
            )
            db.add(seller)
            db.flush()
            added.append(f"seller {data['name']}")
        sellers[data["slug"]] = seller

    request_text_by_job = {job["id"]: job["request_text"] for job in JOBS}
    for data in JOBS:
        job = db.get(Job, data["id"])
        if job is None:
            db.add(
                Job(
                    id=data["id"],
                    user_id=user.id,
                    seller_id=sellers[data["seller"]].id,
                    request_text=data["request_text"],
                    category="coding",
                    status=data["status"],
                    acceptance_tests_json=json.dumps(data["tests"]),
                    test_code=data.get("test_code"),
                    created_at=ts(data["created_at"]),
                )
            )
            added.append(f"job {data['id']}")
        elif data.get("test_code") and not job.test_code:
            job.test_code = data["test_code"]
            added.append(f"tests for job {data['id']}")
    db.flush()

    for data in PAYMENTS:
        if db.get(Payment, data["id"]) is not None:
            continue
        db.add(
            Payment(
                id=data["id"],
                user_id=user.id,
                seller_id=sellers[data["seller"]].id,
                job_id=data["job"],
                amount_cents=data["amount_cents"],
                description=request_text_by_job[data["job"]],
                state=PaymentState(data["status"]),
                decision_json=json.dumps(data["decision"]),
                paypal_authorization_id=data["funding_ref"],
                payout_ref=data["payout_ref"],
                refund_ref=data["refund_ref"],
                created_at=ts(data["created_at"]),
                updated_at=ts(data["updated_at"]),
            )
        )
        db.flush()
        previous = None
        for status, at, note in data["history"]:
            db.add(
                PaymentEvent(
                    payment_id=data["id"],
                    from_state=previous,
                    to_state=status,
                    reason=note,
                    created_at=ts(at),
                )
            )
            previous = status
        added.append(f"payment {data['id']}")
    db.flush()

    for number, payment_number, at, actor, action, verdict, reason, details in AUDIT:
        if db.get(AuditEntry, number) is None:
            db.add(
                AuditEntry(
                    id=number,
                    payment_id=payment_number,
                    actor=actor,
                    action=action,
                    verdict=verdict,
                    reason=reason,
                    details_json=json.dumps(details),
                    created_at=ts(at),
                )
            )
            added.append(f"audit entry {number}")
    db.flush()
    return added


def seed() -> None:
    with SessionLocal() as db:
        added = seed_demo_data(db)
        db.commit()
    if added:
        print("Added: " + ", ".join(added))
    else:
        print("Nothing to add: the demo data is already there.")


if __name__ == "__main__":
    seed()
