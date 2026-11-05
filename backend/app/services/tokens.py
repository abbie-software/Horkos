from datetime import UTC, datetime, timedelta

import jwt

from app.config import settings
from app.errors import ApiError

TOKEN_HOURS = 12
MIN_SECRET_LENGTH = 16
ALGORITHM = "HS256"


def secret() -> str:
    """The signing secret. Without a real one, nobody can log in."""
    value = settings.jwt_secret
    if len(value) < MIN_SECRET_LENGTH:
        raise ApiError(
            500,
            "server_error",
            "Login is not set up: JWT_SECRET is missing or too short.",
        )
    return value


def issue_token(user_id: int, now: datetime | None = None) -> str:
    now = now or datetime.now(UTC)
    claims = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(hours=TOKEN_HOURS),
    }
    return jwt.encode(claims, secret(), algorithm=ALGORITHM)


def read_token(token: str) -> int:
    """The user ID inside a valid token. Anything else is a 401."""
    try:
        claims = jwt.decode(
            token,
            secret(),
            algorithms=[ALGORITHM],  # a token that claims no signature is refused
            options={"require": ["exp", "sub"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise ApiError(401, "unauthorized", "Your session has expired. Log in again.") from exc
    except jwt.InvalidTokenError as exc:
        raise ApiError(401, "unauthorized", "Invalid token. Log in again.") from exc

    subject = str(claims["sub"])
    if not subject.isdigit():
        raise ApiError(401, "unauthorized", "Invalid token. Log in again.")
    return int(subject)
