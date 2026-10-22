import pytest

from app.services.oath import OathParseError, parse_policy

DEMO_OATH = (
    "Spend up to $50 per job and $100 per day. Only on coding work. "
    "Ask me before anything over $30, and always ask me about a seller "
    "I have not used before."
)
SUGGESTED_CLAUSES = (
    "Never spend over $50 per job. Spend at most $100 per day. "
    "Ask me before anything over $30. "
    "Always ask me about a seller I have not used before. Only allow coding work."
)
BASE = "Spend up to $50 per job and $100 per day."
EXPECTED = {
    "per_job_cap_cents": 5000,
    "daily_cap_cents": 10000,
    "ask_threshold_cents": 3000,
    "allowed_categories": ["coding"],
    "blocked_categories": [],
    "ask_for_new_sellers": True,
}


def test_demo_oath_from_the_api_contract():
    assert parse_policy(DEMO_OATH).model_dump() == EXPECTED


def test_the_five_suggested_clauses_from_the_oath_page():
    assert parse_policy(SUGGESTED_CLAUSES).model_dump() == EXPECTED


def test_decimals_and_commas_become_exact_cents():
    policy = parse_policy("Spend up to $25.50 per job and $1,000 per day.")
    assert policy.per_job_cap_cents == 2550
    assert policy.daily_cap_cents == 100000
    assert policy.ask_threshold_cents == 2550


def test_a_day_and_a_job_wording():
    policy = parse_policy("Spend up to $50 a job and $100 a day.")
    assert (policy.per_job_cap_cents, policy.daily_cap_cents) == (5000, 10000)


def test_the_lowest_limit_wins():
    text = "Spend up to $50 per job. Never spend over $20 per job. $100 per day."
    assert parse_policy(text).per_job_cap_cents == 2000


def test_the_ask_amount_is_not_mistaken_for_a_cap():
    policy = parse_policy(BASE + " Ask me before anything over $30 per job.")
    assert policy.per_job_cap_cents == 5000
    assert policy.ask_threshold_cents == 3000


def test_an_ask_amount_above_the_cap_is_lowered_to_the_cap():
    policy = parse_policy(BASE + " Ask me before anything over $80.")
    assert policy.ask_threshold_cents == 5000


def test_blocked_category():
    policy = parse_policy(BASE + " Never pay for gambling work.")
    assert policy.blocked_categories == ["gambling"]


def test_unfamiliar_category_is_kept_when_the_oath_says_work():
    policy = parse_policy(BASE + " Only tutoring work.")
    assert policy.allowed_categories == ["tutoring"]


def test_no_category_rule_leaves_the_lists_empty():
    policy = parse_policy(BASE)
    assert policy.allowed_categories == []
    assert policy.blocked_categories == []


def test_never_allow_payments_over_is_not_a_category():
    policy = parse_policy(BASE + " Never allow payments over $40.")
    assert policy.blocked_categories == []


def test_new_seller_rule_is_off_unless_the_oath_asks_for_it():
    assert parse_policy(BASE).ask_for_new_sellers is False


def test_never_ask_about_new_sellers_does_not_switch_the_rule_on():
    policy = parse_policy(BASE + " Never ask me about new sellers.")
    assert policy.ask_for_new_sellers is False


def test_missing_daily_limit_is_rejected_with_a_helpful_message():
    with pytest.raises(OathParseError, match="each day"):
        parse_policy("Spend up to $50 per job.")


def test_missing_job_limit_is_rejected_with_a_helpful_message():
    with pytest.raises(OathParseError, match="each job"):
        parse_policy("Spend at most $100 per day.")


def test_empty_oath_is_rejected():
    with pytest.raises(OathParseError, match="Write your oath"):
        parse_policy("   ")


def test_zero_limits_are_rejected():
    with pytest.raises(OathParseError, match=r"above \$0"):
        parse_policy("Spend up to $0 per job and $100 per day.")