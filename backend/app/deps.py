from typing import Annotated

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import SessionLocal, get_db
from app.errors import ApiError
from app.models import User
from app.services.buyer_agent import GeminiBuyerAgent
from app.services.funding import SimulatedFunder
from app.services.intent import GeminiIntentChecker
from app.services.sandbox import run_in_sandbox

DEMO_EMAIL = "amara@example.com"


def get_current_user(db: Annotated[Session, Depends(get_db)]) -> User:
    """TEMPORARY stand-in until login exists: every caller is the demo user.

    Replace this with a Bearer-token check when POST /auth/login is built.
    """
    user = db.scalar(select(User).where(User.email == DEMO_EMAIL))
    if user is None:
        raise ApiError(
            401,
            "unauthorized",
            "Demo user not found. Run: python -m app.scripts.seed",
        )
    return user


def get_buyer_agent() -> GeminiBuyerAgent:
    return GeminiBuyerAgent()


def get_intent_checker() -> GeminiIntentChecker:
    return GeminiIntentChecker()


def get_funder() -> SimulatedFunder:
    return SimulatedFunder()


def get_session_factory():
    return SessionLocal


def get_runner():
    return run_in_sandbox
