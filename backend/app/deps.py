from typing import Annotated

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal, get_db
from app.errors import ApiError
from app.models import User
from app.services.buyer_agent import GeminiBuyerAgent
from app.services.funding import SimulatedFunder
from app.services.intent import GeminiIntentChecker
from app.services.sandbox import run_in_sandbox
from app.services.streaming import StreamSettings

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


def get_stream_settings() -> StreamSettings:
    return StreamSettings()


def check_stream_token(token: str | None = None) -> str | None:
    """TEMPORARY: the browser's EventSource cannot send headers, so the contract
    puts the token in the query string. Check it here once login exists."""
    return token


def get_demo_enabled() -> bool:
    return settings.demo_controls


def check_demo_enabled(enabled: Annotated[bool, Depends(get_demo_enabled)]) -> None:
    """The demo controls can wipe the data, so they can be switched off."""
    if not enabled:
        raise ApiError(404, "not_found", "Not found.")


def get_attack_pause() -> float:
    """Seconds between the steps of an attack, so the Live Feed is easy to follow."""
    return 1.0
