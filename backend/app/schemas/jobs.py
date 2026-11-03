from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.payments import PaymentOut

JobStatus = Literal[
    "open", "awaiting_work", "verifying", "completed", "failed", "cancelled"
]


class JobIn(BaseModel):
    request_text: str = Field(min_length=1, max_length=2000)
    seller_id: str | None = None


class DecisionIn(BaseModel):
    decision: Literal["approve", "reject"]


class JobOut(BaseModel):
    """A job as the API returns it. Matches the Job type in the API contract."""

    id: str
    request_text: str
    category: str
    status: JobStatus
    seller_id: str
    payment_id: str | None
    acceptance_tests: list[str]
    created_at: datetime

class JobList(BaseModel):
    items: list[JobOut]
    total: int

class JobCreated(BaseModel):
    job: JobOut
    payment: PaymentOut


class SubmissionIn(BaseModel):
    seller_id: str
    content: str = Field(min_length=1, max_length=50_000)


class SubmissionAccepted(BaseModel):
    submission_id: str
    status: Literal["verifying"] = "verifying"
    payment_id: str
