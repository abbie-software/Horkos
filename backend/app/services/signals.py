import re
from dataclasses import dataclass

from app.schemas.oath import Policy
from app.schemas.payments import SIGNAL_CODES, SignalOut
from app.services.hard_rules import Proposal, SellerFacts

# What each triggered signal adds to the risk score. recipient_changed is a
# hard rule, so it never adds to the soft score.
SIGNAL_WEIGHTS: dict[str, int] = {
    "intent_mismatch": 40,
    "edge_of_limit": 25,
    "velocity": 20,
    "unproven_seller": 20,
    "pressure_language": 25,
}

VELOCITY_PROPOSALS = 3  # this many proposals within the window is a burst
NEW_BAND_TOP = 25  # trust scores up to here are in the "new" band

# Phrases that push the reviewer to skip checks or pay right away.
PRESSURE_PHRASES = [
    "pay immediately",
    "pay me now",
    "pay now",
    "pay right now",
    "pay asap",
    "payment immediately",
    "immediate payment",
    "urgent payment",
    "release the money now",
    "release payment now",
    "skip the review",
    "skip review",
    "skip the check",
    "skip the checks",
    "skip verification",
    "skip the verification",
    "no need to review",
    "no need to check",
    "no need to verify",
    "don't review",
    "do not review",
    "don't check",
    "do not check",
    "don't verify",
    "do not verify",
    "without review",
    "without checking",
    "without verifying",
]
PRESSURE_PATTERN = re.compile(
    r"\b(?:"
    + "|".join(re.escape(p) for p in sorted(PRESSURE_PHRASES, key=len, reverse=True))
    + r")\b",
    re.IGNORECASE,
)

NO_CONCERN = "No concern found."


@dataclass(frozen=True)
class IntentResult:
    """The Auditor's answer. mismatch is None when it could not tell."""

    mismatch: bool | None
    detail: str = ""


@dataclass(frozen=True)
class Activity:
    """Recent behaviour by this user, worked out from the database."""

    spent_today_cents: int = 0
    recent_proposals: int = 0  # proposals in the last 10 minutes
    recent_blocks: int = 0  # blocked payments in the last 10 minutes


def times_text(amount_cents: int, limit_cents: int) -> str:
    """'2.5' for 2500 against 1000, using integer math."""
    tenths = (amount_cents * 10 + limit_cents // 2) // limit_cents
    return f"{tenths // 10}.{tenths % 10}"


def assess_signals(
    proposal: Proposal,
    seller: SellerFacts,
    policy: Policy,
    request_text: str,
    activity: Activity,
    intent: IntentResult,
) -> list[SignalOut]:
    """All six signals, in the contract's order, triggered or not."""
    found: dict[str, str] = {}

    if intent.mismatch is True:
        found["intent_mismatch"] = (
            intent.detail or "The payment does not match what you asked for."
        )

    if seller.limit_cents > 0 and proposal.amount_cents > seller.limit_cents:
        times = times_text(proposal.amount_cents, seller.limit_cents)
        found["edge_of_limit"] = f"Amount is {times} times this seller's current limit."
    elif proposal.amount_cents * 10 >= policy.per_job_cap_cents * 9:
        found["edge_of_limit"] = "Amount is within 10% of your per-job cap."

    if activity.recent_blocks >= 1:
        found["velocity"] = "A payment was blocked a few minutes ago and this is a retry."
    elif activity.recent_proposals >= VELOCITY_PROPOSALS:
        found["velocity"] = (
            f"{activity.recent_proposals} payments were proposed in the last 10 minutes."
        )

    if seller.jobs_completed == 0:
        found["unproven_seller"] = f"{seller.name} has no completed jobs yet."
    elif seller.trust_score <= NEW_BAND_TOP:
        found["unproven_seller"] = (
            f"{seller.name} has a low trust score ({seller.trust_score})."
        )

    match = PRESSURE_PATTERN.search(request_text.replace("\u2019", "'"))
    if match:
        found["pressure_language"] = f"The message said '{match.group(0)}'."

    signals = []
    for code in SIGNAL_CODES:
        signals.append(
            SignalOut(
                code=code,
                triggered=code in found,
                detail=found.get(code, NO_CONCERN),
            )
        )
    return signals


def risk_score(seller: SellerFacts, signals: list[SignalOut]) -> int:
    """A starting score from the seller's trust, plus the weight of each triggered signal."""
    score = max(0, 100 - seller.trust_score) // 10
    score += sum(SIGNAL_WEIGHTS.get(s.code, 0) for s in signals if s.triggered)
    return min(100, score)