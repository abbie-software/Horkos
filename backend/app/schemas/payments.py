from datetime import datetime
from typing import Literal

from pydantic import BaseModel

PaymentStatus = Literal[
    "proposed",
    "awaiting_user",
    "approved",
    "held",
    "verified",
    "released",
    "refunded",
    "blocked",
]
Verdict = Literal["approve", "block", "ask"]
RiskLevel = Literal["low", "medium", "high"]
HardRule = Literal[
    "recipient_changed", "over_cap", "excluded_category", "blocklisted_or_low_trust"
]
SignalCode = Literal[
    "intent_mismatch",
    "recipient_changed",
    "edge_of_limit",
    "velocity",
    "unproven_seller",
    "pressure_language",
]

# Every decision lists all six signals, triggered or not, in this order.
SIGNAL_CODES: list[SignalCode] = [
    "intent_mismatch",
    "recipient_changed",
    "edge_of_limit",
    "velocity",
    "unproven_seller",
    "pressure_language",
]


class SignalOut(BaseModel):
    code: SignalCode
    triggered: bool
    detail: str


class DecisionOut(BaseModel):
    verdict: Verdict
    risk_score: int
    risk_level: RiskLevel
    reason: str
    hard_rule: HardRule | None
    signals: list[SignalOut]


class TransitionOut(BaseModel):
    status: PaymentStatus
    at: datetime
    note: str


class PaypalRefs(BaseModel):
    funding_ref: str | None
    payout_ref: str | None
    refund_ref: str | None


class PaymentOut(BaseModel):
    """A payment as the API returns it. Matches the Payment type in the API contract."""

    id: str
    job_id: str | None
    seller_id: str
    seller_name: str
    amount_cents: int
    currency: Literal["USD"] = "USD"
    status: PaymentStatus
    decision: DecisionOut
    history: list[TransitionOut]
    paypal: PaypalRefs
    created_at: datetime
    updated_at: datetime


class PaymentList(BaseModel):
    items: list[PaymentOut]
    total: int