from datetime import UTC

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Oath
from app.schemas.oath import OathOut, Policy
from app.services.oath import parse_policy


def save_oath(db: Session, user_id: int, raw_text: str) -> Oath:
    """Save a new version of the user's oath. A bad oath raises before anything is written."""
    policy = parse_policy(raw_text)
    oath = Oath(
        user_id=user_id,
        text=raw_text.strip(),
        policy_json=policy.model_dump_json(),
    )
    db.add(oath)
    db.flush()
    return oath


def get_latest_oath(db: Session, user_id: int) -> Oath | None:
    return db.scalars(
        select(Oath).where(Oath.user_id == user_id).order_by(Oath.id.desc()).limit(1)
    ).first()


def oath_to_out(oath: Oath) -> OathOut:
    stamp = oath.created_at
    if stamp.tzinfo is None:  # SQLite hands back times without a timezone
        stamp = stamp.replace(tzinfo=UTC)
    return OathOut(
        id=f"oath_{oath.id}",
        raw_text=oath.text,
        policy=Policy.model_validate_json(oath.policy_json),
        updated_at=stamp,
    )