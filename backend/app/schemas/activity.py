from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel

Actor = Literal["user", "buyer_agent", "guard", "verifier", "system"]
EventType = Literal[
    "payment.proposed",
    "payment.verdict",
    "payment.status_changed",
    "verification.result",
    "trust.updated",
    "demo.attack_started",
    "demo.reset",
]


class AuditOut(BaseModel):
    """An audit trail entry. Matches the AuditEntry type in the API contract."""

    id: str
    payment_id: str
    at: datetime
    actor: Actor
    action: str
    verdict: Literal["approve", "block", "ask"] | None
    reason: str
    details: dict[str, Any]


class AuditList(BaseModel):
    items: list[AuditOut]
    total: int


class EventOut(BaseModel):
    """A Live Feed event. Matches the HorkosEvent type in the API contract."""

    id: str
    type: EventType
    at: datetime
    payment_id: str | None
    seller_id: str | None
    message: str
    payload: dict[str, Any]
