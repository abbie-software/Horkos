from typing import Literal

from pydantic import BaseModel, Field


class LoginIn(BaseModel):
    email: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=1, max_length=200)

class SignupIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=1, max_length=200)
    role: Literal["buyer", "seller"] = "buyer"
    paypal_email: str | None = Field(default=None, max_length=255)

class UserOut(BaseModel):
    id: str
    name: str
    email: str
    role: Literal["buyer", "seller"] = "buyer"
    seller_id: str | None = None


class LoginOut(BaseModel):
    """Matches POST /auth/login in the API contract."""

    access_token: str
    token_type: Literal["bearer"] = "bearer"
    user: UserOut
