from dataclasses import dataclass

from app.schemas.oath import Policy
from app.schemas.payments import SIGNAL_CODES, DecisionOut, HardRule, SignalOut
from app.services.risk import risk_level_for

# A seller who has failed jobs and falls below this score is blocked outright.
# New sellers have a score of 0 but no failures, so they are asked about, not blocked.
TRUST_FLOOR = 5

# Every hard block is in the high band (67-100).
RISK_SCORES: dict[str, int] = {
    "recipient_changed": 97,
    "over_cap": 92,
    "blocklisted_or_low_trust": 90,
    "excluded_category": 88,
}


@dataclass(frozen=True)
class Proposal:
    """A payment the Buyer Agent wants to make."""

    amount_cents: int
    category: str
    recipient_email: str  # the PayPal account the money would go to


@dataclass(frozen=True)
class SellerFacts:
    """What the Guard knows about the seller."""

    name: str
    agreed_email: str  # the PayPal account agreed at the start of the job
    trust_score: int
    jobs_failed: int = 0
    blocklisted: bool = False


@dataclass(frozen=True)
class HardRuleHit:
    code: HardRule
    reason: str
    risk_score: int


def dollars(cents: int) -> str:
    """Whole cents to a price, using integer math only: 5000 -> $50.00."""
    return f"${cents // 100:,}.{cents % 100:02d}"


def hit(code: HardRule, reason: str) -> HardRuleHit:
    return HardRuleHit(code=code, reason=reason, risk_score=RISK_SCORES[code])


def check_hard_rules(
    proposal: Proposal,
    seller: SellerFacts,
    policy: Policy,
    spent_today_cents: int = 0,
) -> HardRuleHit | None:
    """Return the first hard rule the payment breaks, or None.

    Hard rules are plain code, with no AI. They run in a fixed order and the
    first one that fires decides the outcome. Nothing can override a hit.
    """
    if proposal.amount_cents <= 0:
        raise ValueError("A payment must be for a positive number of cents")

    # 1. The recipient must be the account agreed at the start of the job.
    if proposal.recipient_email.strip().lower() != seller.agreed_email.strip().lower():
        return hit(
            "recipient_changed",
            f"Blocked: the recipient changed from {seller.name} to a different "
            "account in the middle of the job.",
        )

    # 2. The oath's spending caps.
    if proposal.amount_cents > policy.per_job_cap_cents:
        return hit(
            "over_cap",
            f"Blocked: {dollars(proposal.amount_cents)} is above your "
            f"{dollars(policy.per_job_cap_cents)} per-job cap. "
            "This rule has no exceptions.",
        )
    total_today = spent_today_cents + proposal.amount_cents
    if total_today > policy.daily_cap_cents:
        return hit(
            "over_cap",
            f"Blocked: this payment would bring today's spending to "
            f"{dollars(total_today)}, above your {dollars(policy.daily_cap_cents)} "
            "daily cap. This rule has no exceptions.",
        )

    # 3. The oath's categories.
    category = proposal.category.strip().lower()
    if category in policy.blocked_categories:
        return hit(
            "excluded_category",
            f"Blocked: you excluded {category} work in your oath. "
            "This rule has no exceptions.",
        )
    if policy.allowed_categories and category not in policy.allowed_categories:
        allowed = ", ".join(policy.allowed_categories)
        return hit(
            "excluded_category",
            f"Blocked: your oath allows only {allowed} work, and this job is "
            f"{category}. This rule has no exceptions.",
        )

    # 4. The seller must not be blocklisted or burned by failed work.
    if seller.blocklisted:
        return hit(
            "blocklisted_or_low_trust",
            f"Blocked: {seller.name} is on your blocklist. This rule has no exceptions.",
        )
    if seller.jobs_failed > 0 and seller.trust_score < TRUST_FLOOR:
        return hit(
            "blocklisted_or_low_trust",
            f"Blocked: {seller.name}'s trust score ({seller.trust_score}) is below "
            "the minimum after failed work. This rule has no exceptions.",
        )

    return None


def hard_rule_decision(rule: HardRuleHit) -> DecisionOut:
    """The contract's Decision for a payment a hard rule blocked."""
    signals = []
    for code in SIGNAL_CODES:
        if code == "recipient_changed" and rule.code == "recipient_changed":
            signals.append(
                SignalOut(
                    code=code,
                    triggered=True,
                    detail="Payout account differs from the one agreed at the start of the job.",
                )
            )
        else:
            signals.append(
                SignalOut(
                    code=code,
                    triggered=False,
                    detail="Not assessed: a hard rule already blocked this payment.",
                )
            )
    return DecisionOut(
        verdict="block",
        risk_score=rule.risk_score,
        risk_level=risk_level_for(rule.risk_score),
        reason=rule.reason,
        hard_rule=rule.code,
        signals=signals,
    )