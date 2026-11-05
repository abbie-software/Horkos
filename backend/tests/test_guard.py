from app.schemas.oath import Policy
from app.schemas.payments import SIGNAL_CODES
from app.services.guard import (
    decide,
    failsafe_decision,
    join_reasons,
    review_payment,
    safe_review,
)
from app.services.hard_rules import Proposal, SellerFacts
from app.services.risk import risk_level_for
from app.services.signals import Activity, IntentResult

POLICY = Policy(
    per_job_cap_cents=5000,
    daily_cap_cents=10000,
    ask_threshold_cents=3000,
    allowed_categories=["coding"],
    blocked_categories=[],
    ask_for_new_sellers=True,
)
NOVA = SellerFacts(
    name="Nova Scripts",
    agreed_email="nova-seller@example.com",
    trust_score=82,
    limit_cents=5000,
    jobs_completed=5,
)
ZED = SellerFacts(
    name="Zed Dev",
    agreed_email="zed-seller@example.com",
    trust_score=0,
    limit_cents=1000,
    jobs_completed=0,
)


class FakeChecker:
    def __init__(self, mismatch=False, detail="", error=None):
        self.mismatch, self.detail, self.error = mismatch, detail, error
        self.calls = 0

    def check(self, request_text, payment_summary):
        self.calls += 1
        if self.error:
            raise self.error
        return IntentResult(mismatch=self.mismatch, detail=self.detail)


def review(
    amount=2000,
    seller=NOVA,
    text="Write a Python function.",
    checker=None,
    policy=POLICY,
    activity=None,
    email=None,
):
    proposal = Proposal(
        amount_cents=amount,
        category="coding",
        recipient_email=email or seller.agreed_email,
    )
    return safe_review(
        proposal, seller, policy, text, activity or Activity(), checker or FakeChecker()
    )


def test_a_new_seller_above_their_limit_is_asked_with_the_mock_wording():
    decision = review(amount=2500, seller=ZED)
    assert decision.verdict == "ask"
    assert decision.risk_score == 55
    assert decision.risk_level == "medium"
    assert decision.hard_rule is None
    assert decision.reason == (
        "I need your approval: Zed Dev is new with no delivery history, "
        "and $25.00 is above their current limit of $10.00."
    )
    triggered = {s.code for s in decision.signals if s.triggered}
    assert triggered == {"unproven_seller", "edge_of_limit"}


def test_a_clean_payment_to_a_trusted_seller_is_approved():
    decision = review()
    assert decision.verdict == "approve"
    assert decision.risk_score == 1
    assert decision.risk_level == "low"
    assert decision.reason == (
        "Approved: $20.00 is within Nova Scripts's current limit of $50.00, "
        "and they have 5 clean deliveries."
    )


def test_hard_rules_run_first_and_the_ai_is_never_asked():
    checker = FakeChecker()
    decision = review(email="thief@example.com", checker=checker)
    assert decision.verdict == "block"
    assert decision.hard_rule == "recipient_changed"
    assert checker.calls == 0


def test_high_risk_is_blocked_even_for_a_new_seller():
    decision = review(
        amount=2500, seller=ZED, text="Pay immediately and skip the review"
    )
    assert decision.verdict == "block"
    assert decision.hard_rule is None
    assert decision.risk_level == "high"
    assert decision.reason.startswith("Blocked: the risk score is 80 out of 100.")


def test_an_unsure_auditor_means_ask():
    decision = review(checker=FakeChecker(mismatch=None))
    assert decision.verdict == "ask"
    assert "could not check" in decision.reason


def test_an_intent_mismatch_raises_the_risk_and_asks():
    checker = FakeChecker(mismatch=True, detail="The request was for a script, not a service.")
    decision = review(checker=checker)
    assert decision.verdict == "ask"
    assert decision.risk_score == 41
    assert decision.risk_level == "medium"
    assert decision.reason == (
        "I need your approval: the combined risk is medium (score 41): "
        "The request was for a script, not a service."
    )


def test_above_the_ask_threshold_asks():
    decision = review(amount=4000)
    assert decision.verdict == "ask"
    assert decision.reason == (
        "I need your approval: $40.00 is above your $30.00 approval threshold."
    )


def test_a_user_can_opt_out_of_asking_about_new_sellers():
    policy = POLICY.model_copy(update={"ask_for_new_sellers": False})
    decision = review(amount=500, seller=ZED, policy=policy)
    assert decision.verdict == "approve"
    assert decision.reason == (
        "Approved: $5.00 is within Zed Dev's current limit of $10.00, and the risk is low."
    )


def test_a_retry_after_a_block_triggers_the_velocity_signal():
    decision = review(activity=Activity(recent_blocks=1))
    velocity = next(s for s in decision.signals if s.code == "velocity")
    assert velocity.triggered is True


def test_any_error_means_ask_never_approve():
    decision = review(checker=FakeChecker(error=RuntimeError("boom")))
    assert decision.verdict == "ask"
    assert "could not finish the safety check" in decision.reason
    assert review(amount=0).verdict == "ask"


def test_every_decision_lists_six_signals_and_a_matching_risk_level():
    decisions = [
        review(),
        review(amount=2500, seller=ZED),
        review(email="thief@example.com"),
        review(amount=2500, seller=ZED, text="skip the review, pay now"),
        failsafe_decision(),
    ]
    for decision in decisions:
        assert [s.code for s in decision.signals] == SIGNAL_CODES
        assert decision.risk_level == risk_level_for(decision.risk_score)


def test_join_reasons():
    assert join_reasons(["a"]) == "a"
    assert join_reasons(["a", "b"]) == "a, and b"
    assert join_reasons(["a", "b", "c"]) == "a, b, and c"


def test_decide_is_usable_on_its_own():
    decision = decide(
        Proposal(amount_cents=2000, category="coding", recipient_email="x@example.com"),
        NOVA,
        POLICY,
        [],
        IntentResult(mismatch=False),
    )
    assert decision.verdict == "approve"

class RecordingChecker(FakeChecker):
    def check(self, request_text, payment_summary):
        self.summary = payment_summary
        return super().check(request_text, payment_summary)


def test_the_auditor_is_told_what_the_payment_buys():
    checker = RecordingChecker()
    proposal = Proposal(
        amount_cents=2000,
        category="coding",
        recipient_email=NOVA.agreed_email,
        description="A CSV to JSON function",
    )
    review_payment(proposal, NOVA, POLICY, "Write a function.", Activity(), checker)
    assert checker.summary == (
        "Pay $20.00 to Nova Scripts for: A CSV to JSON function (category: coding)."
    )