import logging
from typing import Protocol

from app.schemas.oath import Policy
from app.schemas.payments import SIGNAL_CODES, DecisionOut, SignalOut
from app.services.hard_rules import (
    Proposal,
    SellerFacts,
    check_hard_rules,
    dollars,
    hard_rule_decision,
)
from app.services.risk import risk_level_for
from app.services.signals import (
    Activity,
    IntentResult,
    assess_signals,
    risk_score,
)

log = logging.getLogger(__name__)


class IntentChecker(Protocol):
    def check(self, request_text: str, payment_summary: str) -> IntentResult: ...


def join_reasons(parts: list[str]) -> str:
    if len(parts) == 1:
        return parts[0]
    if len(parts) == 2:
        return f"{parts[0]}, and {parts[1]}"
    return ", ".join(parts[:-1]) + f", and {parts[-1]}"


def failsafe_decision() -> DecisionOut:
    """Used when the check itself fails. Any error means Ask, never Approve."""
    return DecisionOut(
        verdict="ask",
        risk_score=50,
        risk_level="medium",
        reason=(
            "I need your approval: I could not finish the safety check, "
            "so I am not approving this on my own."
        ),
        hard_rule=None,
        signals=[
            SignalOut(code=code, triggered=False, detail="Not checked.")
            for code in SIGNAL_CODES
        ],
    )


def decide(
    proposal: Proposal,
    seller: SellerFacts,
    policy: Policy,
    signals: list[SignalOut],
    intent: IntentResult,
) -> DecisionOut:
    """Turn the signals into Approve, Ask or Block. Hard rules have already run."""
    score = risk_score(seller, signals)
    level = risk_level_for(score)
    triggered = [s.detail for s in signals if s.triggered]

    # High combined risk is blocked, even if the amount is small or the seller is new.
    if level == "high":
        return DecisionOut(
            verdict="block",
            risk_score=score,
            risk_level=level,
            reason=f"Blocked: the risk score is {score} out of 100. " + " ".join(triggered),
            hard_rule=None,
            signals=signals,
        )

    asks: list[str] = []
    if intent.mismatch is None:
        asks.append("I could not check whether this matches your request")
    if policy.ask_for_new_sellers and seller.jobs_completed == 0:
        asks.append(f"{seller.name} is new with no delivery history")
    if proposal.amount_cents > policy.ask_threshold_cents:
        asks.append(
            f"{dollars(proposal.amount_cents)} is above your "
            f"{dollars(policy.ask_threshold_cents)} approval threshold"
        )
    if proposal.amount_cents > seller.limit_cents:
        asks.append(
            f"{dollars(proposal.amount_cents)} is above their current limit "
            f"of {dollars(seller.limit_cents)}"
        )
    if not asks and level == "medium":
        asks.append(
            f"the combined risk is medium (score {score}): " + "; ".join(triggered)
        )

    if asks:
        reason = "I need your approval: " + join_reasons(asks)
        if not reason.endswith("."):
            reason += "."
        return DecisionOut(
            verdict="ask",
            risk_score=score,
            risk_level=level,
            reason=reason,
            hard_rule=None,
            signals=signals,
        )

    record = ""
    if seller.jobs_completed > 0 and seller.jobs_failed == 0:
        word = "delivery" if seller.jobs_completed == 1 else "deliveries"
        record = f", and they have {seller.jobs_completed} clean {word}"
    return DecisionOut(
        verdict="approve",
        risk_score=score,
        risk_level=level,
        reason=(
            f"Approved: {dollars(proposal.amount_cents)} is within {seller.name}'s "
            f"current limit of {dollars(seller.limit_cents)}{record or ', and the risk is low'}."
        ),
        hard_rule=None,
        signals=signals,
    )


def review_payment(
    proposal: Proposal,
    seller: SellerFacts,
    policy: Policy,
    request_text: str,
    activity: Activity,
    checker: IntentChecker,
) -> DecisionOut:
    """Run the Guard: hard rules first, then the signals and the Auditor."""
    rule = check_hard_rules(proposal, seller, policy, activity.spent_today_cents)
    if rule is not None:
        return hard_rule_decision(rule)

    if proposal.description:
        summary = (
            f"Pay {dollars(proposal.amount_cents)} to {seller.name} for: "
            f"{proposal.description} (category: {proposal.category})."
        )
    else:
        summary = (
            f"Pay {dollars(proposal.amount_cents)} to {seller.name} "
            f"for a {proposal.category} job."
        )

    intent = checker.check(request_text, summary)
    signals = assess_signals(proposal, seller, policy, request_text, activity, intent)
    return decide(proposal, seller, policy, signals, intent)


def safe_review(*args, **kwargs) -> DecisionOut:
    """review_payment, but any error becomes Ask. Nothing is approved by accident."""
    try:
        return review_payment(*args, **kwargs)
    except Exception:
        log.exception("The Guard could not finish its check")
        return failsafe_decision()