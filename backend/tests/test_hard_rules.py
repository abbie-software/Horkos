from app.schemas.oath import Policy
from app.services.hard_rules import (
    RISK_SCORES,
    TRUST_FLOOR,
    Proposal,
    SellerFacts,
    check_hard_rules,
    dollars,
    hard_rule_decision,
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
)


def proposal(**changes):
    values = {
        "amount_cents": 2000,
        "category": "coding",
        "recipient_email": "nova-seller@example.com",
    }
    values.update(changes)
    return Proposal(**values)


def test_a_clean_payment_breaks_no_hard_rule():
    assert check_hard_rules(proposal(), NOVA, POLICY) is None


def test_dollars_uses_whole_cents():
    assert dollars(5000) == "$50.00"
    assert dollars(2550) == "$25.50"
    assert dollars(5) == "$0.05"
    assert dollars(100000) == "$1,000.00"


def test_recipient_changed_matches_the_mock_payment():
    result = check_hard_rules(proposal(recipient_email="thief@example.com"), NOVA, POLICY)
    assert result.code == "recipient_changed"
    assert result.reason == (
        "Blocked: the recipient changed from Nova Scripts to a different "
        "account in the middle of the job."
    )


def test_recipient_email_ignores_case_and_spaces():
    same = proposal(recipient_email="  Nova-Seller@Example.com ")
    assert check_hard_rules(same, NOVA, POLICY) is None


def test_over_the_per_job_cap_matches_the_mock_payment():
    result = check_hard_rules(proposal(amount_cents=50000), NOVA, POLICY)
    assert result.code == "over_cap"
    assert result.reason == (
        "Blocked: $500.00 is above your $50.00 per-job cap. This rule has no exceptions."
    )


def test_exactly_the_cap_is_allowed_and_one_cent_over_is_blocked():
    assert check_hard_rules(proposal(amount_cents=5000), NOVA, POLICY) is None
    assert check_hard_rules(proposal(amount_cents=5001), NOVA, POLICY).code == "over_cap"


def test_the_daily_cap_counts_what_was_already_spent_today():
    assert check_hard_rules(proposal(amount_cents=4000), NOVA, POLICY, 6000) is None
    result = check_hard_rules(proposal(amount_cents=4001), NOVA, POLICY, 6000)
    assert result.code == "over_cap"
    assert "$100.01" in result.reason
    assert "daily cap" in result.reason


def test_a_blocked_category_is_refused():
    policy = POLICY.model_copy(update={"allowed_categories": [], "blocked_categories": ["gambling"]})
    result = check_hard_rules(proposal(category="Gambling"), NOVA, policy)
    assert result.code == "excluded_category"
    assert "gambling" in result.reason


def test_a_category_outside_the_allowed_list_is_refused():
    result = check_hard_rules(proposal(category="design"), NOVA, POLICY)
    assert result.code == "excluded_category"
    assert "allows only coding" in result.reason


def test_no_category_rules_means_any_category_passes():
    policy = POLICY.model_copy(update={"allowed_categories": []})
    assert check_hard_rules(proposal(category="design"), NOVA, policy) is None


def test_a_blocklisted_seller_is_refused():
    seller = SellerFacts(
        name="Nova Scripts",
        agreed_email=NOVA.agreed_email,
        trust_score=82,
        blocklisted=True,
    )
    result = check_hard_rules(proposal(), seller, POLICY)
    assert result.code == "blocklisted_or_low_trust"
    assert "blocklist" in result.reason


def test_failed_work_and_a_score_under_the_floor_is_refused():
    burned = SellerFacts(
        name="QuickPay Dev",
        agreed_email=NOVA.agreed_email,
        trust_score=TRUST_FLOOR - 1,
        jobs_failed=3,
    )
    assert check_hard_rules(proposal(), burned, POLICY).code == "blocklisted_or_low_trust"


def test_a_new_seller_with_a_zero_score_is_not_blocked():
    new = SellerFacts(name="Zed Dev", agreed_email=NOVA.agreed_email, trust_score=0)
    assert check_hard_rules(proposal(), new, POLICY) is None


def test_the_demo_restricted_seller_is_not_hard_blocked():
    quick = SellerFacts(
        name="QuickPay Dev",
        agreed_email=NOVA.agreed_email,
        trust_score=9,
        jobs_failed=2,
    )
    assert check_hard_rules(proposal(amount_cents=500), quick, POLICY) is None


def test_the_first_rule_that_fires_decides():
    messy = proposal(amount_cents=50000, category="design", recipient_email="thief@example.com")
    assert check_hard_rules(messy, NOVA, POLICY).code == "recipient_changed"
    messy = proposal(amount_cents=50000, category="design")
    assert check_hard_rules(messy, NOVA, POLICY).code == "over_cap"
    messy = proposal(category="design")
    assert check_hard_rules(messy, NOVA, POLICY).code == "excluded_category"


def test_a_payment_of_zero_or_less_is_an_error_not_an_approval():
    for bad in (0, -100):
        try:
            check_hard_rules(proposal(amount_cents=bad), NOVA, POLICY)
        except ValueError:
            continue
        raise AssertionError(f"{bad} cents was accepted")


def test_every_hard_block_is_in_the_high_risk_band():
    assert set(RISK_SCORES) == {
        "recipient_changed",
        "over_cap",
        "excluded_category",
        "blocklisted_or_low_trust",
    }
    assert all(67 <= score <= 100 for score in RISK_SCORES.values())


def test_the_decision_for_a_hard_block_follows_the_contract():
    rule = check_hard_rules(proposal(recipient_email="thief@example.com"), NOVA, POLICY)
    decision = hard_rule_decision(rule)
    assert decision.verdict == "block"
    assert decision.hard_rule == "recipient_changed"
    assert decision.risk_score == 97
    assert decision.risk_level == "high"
    assert len(decision.signals) == 6
    triggered = [s.code for s in decision.signals if s.triggered]
    assert triggered == ["recipient_changed"]