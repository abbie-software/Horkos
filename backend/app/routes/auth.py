import re
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.errors import ApiError
from app.models import Seller, User
from app.schemas.auth import LoginIn, LoginOut, SignupIn, UserOut
from app.services.accounts import create_account
from app.services.passwords import dummy_hash, verify_password
from app.services.tokens import issue_token
from app.services.views import seller_public_id

router = APIRouter(tags=["auth"])

DbSession = Annotated[Session, Depends(get_db)]


def public_user_id(user: User) -> str:
    """The contract's style of ID, for example usr_amara."""
    return "usr_" + re.sub(r"\W", "", user.name.lower())


def user_out(db: Session, user: User) -> UserOut:
    """The account as the screens see it. A seller account also carries its seller's ID."""
    seller = db.get(Seller, user.seller_id) if user.seller_id else None
    return UserOut(
        id=public_user_id(user),
        name=user.name,
        email=user.email,
        role="seller" if user.role == "seller" else "buyer",
        seller_id=seller_public_id(seller) if seller else None,
    )


@router.post("/auth/login", response_model=LoginOut)
def login(body: LoginIn, db: DbSession):
    email = body.email.strip().lower()
    user = db.scalar(select(User).where(User.email == email))
    # Wrong email and wrong password look the same, in the message and in the time taken.
    stored = user.password_hash if user is not None else dummy_hash()
    if not verify_password(body.password, stored) or user is None:
        raise ApiError(401, "unauthorized", "Wrong email or password.")
    return LoginOut(access_token=issue_token(user.id), user=user_out(db, user))

@router.post("/auth/signup", response_model=LoginOut, status_code=201)
def signup(body: SignupIn, db: DbSession):
    """Make an account and sign it in straight away. Same answer as login."""
    user = create_account(db, body)
    db.commit()
    return LoginOut(access_token=issue_token(user.id), user=user_out(db, user))