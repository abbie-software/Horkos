"""The sentences shown in the Live Feed and the audit trail.

Kept free of database code so the wording can be tested on its own.
"""

from app.schemas.payments import DecisionOut
from app.services.hard_rules import dollars
from app.services.sandbox import SandboxResult

BLOCK_NOTES = {
    "recipient_changed": "recipient changed mid-job.",
    "over_cap": "over your spending cap.",
    "excluded_category": "category not allowed by your oath.",
    "blocklisted_or_low_trust": "seller is blocklisted or not trusted.",
}


def verdict_message(decision: DecisionOut) -> str:
    if decision.verdict == "approve":
        return f"Guard approved the payment ({decision.risk_level} risk)."
    if decision.verdict == "ask":
        return "Guard asked you to decide."
    if decision.hard_rule:
        return f"Guard blocked the payment: {BLOCK_NOTES[decision.hard_rule]}"
    return f"Guard blocked the payment: the risk score is {decision.risk_score} out of 100."


def status_message(new_state: str, seller_name: str, amount_cents: int) -> str:
    amount = dollars(amount_cents)
    return {
        "awaiting_user": "Waiting for your decision.",
        "approved": "Payment approved.",
        "blocked": "Payment blocked.",
        "held": "Funds are being held.",
        "verified": "The work was verified.",
        "released": f"{seller_name} was paid {amount}.",
        "refunded": f"{amount} was refunded to the buyer.",
    }.get(new_state, f"Payment is now {new_state}.")


def check_event_message(result: SandboxResult) -> str:
    if result.status == "passed":
        return f"Work passed {result.passed} of {result.total} tests."
    if result.total > 0:
        return f"Work failed: {result.passed} of {result.total} tests passed."
    return f"Work failed: {result.output_excerpt}"


def check_audit_reason(result: SandboxResult) -> str:
    if result.status == "passed":
        return f"{result.passed} of {result.total} tests passed."
    if result.total > 0:
        return (
            f"{result.passed} of {result.total} tests passed. "
            "The work did not meet the agreed tests."
        )
    return result.output_excerpt


def trust_message(seller_name: str, old: int, new: int, limit_cents: int) -> str:
    verb = "rose" if new > old else "dropped"
    return (
        f"{seller_name}'s trust {verb} from {old} to {new}. "
        f"New limit: {dollars(limit_cents)}."
    )


def trust_audit_reason(seller_name: str, old: int, new: int, limit_cents: int) -> str:
    verb = "rose" if new > old else "dropped"
    return (
        f"{seller_name}'s trust score {verb} from {old} to {new} "
        f"and the limit is now {dollars(limit_cents)}."
    )
