import re
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.errors import ApiError
from app.models import User
from app.schemas.auth import LoginIn, LoginOut, UserOut
from app.services.passwords import dummy_hash, verify_password
from app.services.tokens import issue_token

router = APIRouter(tags=["auth"])

DbSession = Annotated[Session, Depends(get_db)]


def public_user_id(user: User) -> str:
    """The contract's style of ID, for example usr_amara."""
    return "usr_" + re.sub(r"\W", "", user.name.lower())


@router.post("/auth/login", response_model=LoginOut)
def login(body: LoginIn, db: DbSession):
    email = body.email.strip().lower()
    user = db.scalar(select(User).where(User.email == email))
    # Wrong email and wrong password look the same, in the message and in the time taken.
    stored = user.password_hash if user is not None else dummy_hash()
    if not verify_password(body.password, stored) or user is None:
        raise ApiError(401, "unauthorized", "Wrong email or password.")
    return LoginOut(
        access_token=issue_token(user.id),
        user=UserOut(id=public_user_id(user), name=user.name, email=user.email),
    )
