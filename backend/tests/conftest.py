from typing import Annotated

import pytest
from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.deps import check_stream_token, get_current_user
from app.errors import ApiError
from app.main import app
from app.models import User

DEMO_EMAIL = "amara@example.com"


def demo_user(db: Annotated[Session, Depends(get_db)]) -> User:
    user = db.scalar(select(User).where(User.email == DEMO_EMAIL))
    if user is None:
        raise ApiError(401, "unauthorized", "Demo user not found.")
    return user


def skip_stream_token(token: str | None = None) -> str | None:
    return token


@pytest.fixture(autouse=True)
def log_in_as_the_demo_user(request):
    """Most tests are about something other than logging in, so they skip it.
    Tests marked real_auth use the real login check instead."""
    if request.node.get_closest_marker("real_auth") is None:
        app.dependency_overrides[get_current_user] = demo_user
        app.dependency_overrides[check_stream_token] = skip_stream_token
    yield
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(check_stream_token, None)

@pytest.fixture(autouse=True)
def no_local_seller_emails(monkeypatch):
    """A developer's own SELLER_PAYPAL_EMAILS in .env must not change what the tests expect."""
    monkeypatch.setattr(settings, "seller_paypal_emails", "")