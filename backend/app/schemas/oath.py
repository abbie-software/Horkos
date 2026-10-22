from pydantic import BaseModel, Field


class Policy(BaseModel):
    """What Horkos understood from the oath. Matches the Policy type in the API contract."""

    per_job_cap_cents: int
    daily_cap_cents: int
    ask_threshold_cents: int
    allowed_categories: list[str] = Field(default_factory=list)
    blocked_categories: list[str] = Field(default_factory=list)
    ask_for_new_sellers: bool = False