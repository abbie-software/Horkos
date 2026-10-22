from datetime import datetime
from typing import Literal

from pydantic import BaseModel

SellerTier = Literal["new", "building", "trusted", "restricted"]


class SellerOut(BaseModel):
    """A seller as the API returns it. Matches the Seller type in the API contract."""

    id: str
    name: str
    paypal_email: str
    trust_score: int
    tier: SellerTier
    limit_cents: int
    jobs_completed: int
    jobs_failed: int
    last_activity_at: datetime | None


class SellerList(BaseModel):
    items: list[SellerOut]
    total: int