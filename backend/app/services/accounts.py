import re

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.errors import ApiError
from app.models import Seller, User
from app.schemas.auth import SignupIn
from app.services.passwords import hash_password

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
NEW_SELLER_LIMIT_CENTS = 1000  # $10.00, like a brand-new demo seller


def invalid(message: str) -> ApiError:
    return ApiError(422, "validation_error", message)


def email_taken() -> ApiError:
    return ApiError(409, "email_taken", "An account with this email already exists.")


def check_signup(body: SignupIn) -> tuple[str, str, str | None]:
    """Tidy the input and refuse anything unusable.
    Returns the name, the email and (for sellers) the PayPal email."""
    name = body.name.strip()
    email = body.email.strip().lower()
    if not name:
        raise invalid("name: must not be blank")
    if not EMAIL_PATTERN.match(email):
        raise invalid("email: must be a valid email address")
    if len(body.password) < 8:
        raise invalid("password: must be at least 8 characters")
    if not body.password.strip():
        raise invalid("password: must not be only spaces")
    if body.password.strip().lower() == email:
        raise invalid("password: must not be the same as the email")
    paypal_email = None
    if body.role == "seller":
        paypal_email = (body.paypal_email or "").strip().lower()
        if not EMAIL_PATTERN.match(paypal_email):
            raise invalid("paypal_email: a seller needs a valid PayPal email")
    return name, email, paypal_email


def new_seller_slug(db: Session, name: str) -> str:
    """sel_ plus the name, for example sel_otienodev. A taken one gets a number."""
    base = "sel_" + (re.sub(r"[^a-z0-9]", "", name.lower())[:30] or "seller")
    slug, number = base, 1
    while db.scalar(select(Seller).where(Seller.slug == slug)) is not None:
        number += 1
        slug = f"{base}{number}"
    return slug


def create_account(db: Session, body: SignupIn) -> User:
    """Add a buyer, or a seller with its own new seller record. Nothing is committed here."""
    name, email, paypal_email = check_signup(body)
    if db.scalar(select(User).where(User.email == email)) is not None:
        raise email_taken()

    seller = None
    if paypal_email is not None:
        seller = Seller(
            slug=new_seller_slug(db, name),
            name=name,
            paypal_email=paypal_email,
            trust_score=0,
            limit_cents=NEW_SELLER_LIMIT_CENTS,
        )
        db.add(seller)
        db.flush()

    user = User(
        email=email,
        name=name,
        role=body.role,
        seller_id=seller.id if seller else None,
        password_hash=hash_password(body.password),
    )
    db.add(user)
    try:
        db.flush()
    except IntegrityError as exc:  # two sign-ups with the same email at the same moment
        db.rollback()
        raise email_taken() from exc
    return user