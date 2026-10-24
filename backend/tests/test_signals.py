from app.schemas.oath import Policy
from app.schemas.payments import SIGNAL_CODES
from app.services.hard_rules import Proposal, SellerFacts
from app.services.signals import (
    Activity,
    IntentResult,
    assess_signals,
    risk_score,
    times_text,
)

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


def run(amount=2000, seller=NOVA, text="Write a function.", activity=None, intent=None):
    proposal = Proposal(
        amount_cents=amount, category="coding", recipient_email=seller.agreed_email
    )
    return assess_signals(
        proposal,
        seller,
        POLICY,
        text,
        activity or Activity(),
        intent or IntentResult(mismatch=False),
    )


def triggered(signals):
    return {s.code for s in signals if s.triggered}


def detail(signals, code):
    return next(s.detail for s in signals if s.code == code)


def test_a_clean_payment_triggers_nothing_and_lists_all_six_in_order():
    signals = run()
    assert triggered(signals) == set()
    assert [s.code for s in signals] == SIGNAL_CODES


def test_above_the_sellers_limit_matches_the_mock_wording():
    signals = run(amount=2500, seller=ZED)
    assert "edge_of_limit" in triggered(signals)
    assert detail(signals, "edge_of_limit") == "Amount is 2.5 times this seller's current limit."


def test_within_ten_percent_of_the_cap_is_an_edge():
    assert "edge_of_limit" in triggered(run(amount=4500))
    assert "edge_of_limit" not in triggered(run(amount=4499))
    assert detail(run(amount=4500), "edge_of_limit") == "Amount is within 10% of your per-job cap."


def test_velocity_after_a_block_or_a_burst():
    assert "velocity" in triggered(run(activity=Activity(recent_blocks=1)))
    assert "velocity" in triggered(run(activity=Activity(recent_proposals=3)))
    assert "velocity" not in triggered(run(activity=Activity(recent_proposals=2)))


def test_unproven_seller():
    signals = run(seller=ZED, amount=500)
    assert detail(signals, "unproven_seller") == "Zed Dev has no completed jobs yet."
    low = SellerFacts(
        name="Low Trust", agreed_email="a@example.com", trust_score=25,
        limit_cents=1000, jobs_completed=3,
    )
    assert "unproven_seller" in triggered(run(seller=low, amount=500))
    fine = SellerFacts(
        name="Fine", agreed_email="a@example.com", trust_score=26,
        limit_cents=1000, jobs_completed=3,
    )
    assert "unproven_seller" not in triggered(run(seller=fine, amount=500))


def test_pressure_language():
    signals = run(text="Pay immediately, no need to review.")
    assert detail(signals, "pressure_language") == "The message said 'Pay immediately'."
    assert "pressure_language" in triggered(run(text="Please don\u2019t check this."))


def test_ordinary_requests_do_not_trigger_pressure_language():
    for text in (
        "Write a function that returns immediately.",
        "I need this urgent bug fixed in my parser.",
        "Convert a CSV file into JSON.",
    ):
        assert "pressure_language" not in triggered(run(text=text))


def test_intent_mismatch_only_when_the_auditor_says_so():
    bad = run(intent=IntentResult(mismatch=True, detail="The work does not match."))
    assert detail(bad, "intent_mismatch") == "The work does not match."
    assert "intent_mismatch" not in triggered(run(intent=IntentResult(mismatch=False)))
    assert "intent_mismatch" not in triggered(run(intent=IntentResult(mismatch=None)))


def test_risk_score_starts_from_trust_and_adds_signal_weights():
    assert risk_score(NOVA, run()) == 1
    assert risk_score(ZED, run(amount=2500, seller=ZED)) == 55  # 10 + 20 + 25


def test_risk_score_is_capped_at_100():
    signals = run(
        amount=2500,
        seller=ZED,
        text="Pay immediately and skip the review",
        activity=Activity(recent_blocks=1),
        intent=IntentResult(mismatch=True, detail="No match."),
    )
    assert risk_score(ZED, signals) == 100


def test_times_text_uses_integer_math():
    assert times_text(2500, 1000) == "2.5"
    assert times_text(3000, 1000) == "3.0"
    assert times_text(1500, 1000) == "1.5"