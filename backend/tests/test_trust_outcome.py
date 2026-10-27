from types import SimpleNamespace

from app.services.trust import FAIL_PENALTY, LIMITS, PASS_BONUS, apply_outcome


def seller(score, completed=0, failed=0, limit=0):
    return SimpleNamespace(
        trust_score=score,
        jobs_completed=completed,
        jobs_failed=failed,
        limit_cents=limit,
    )


def test_a_pass_raises_the_score_and_counts_the_job():
    kip = seller(46, completed=2, limit=2500)
    assert apply_outcome(kip, passed=True) == (46, 58)
    assert (kip.trust_score, kip.jobs_completed, kip.jobs_failed) == (58, 3, 0)
    assert kip.limit_cents == 2500


def test_a_pass_never_takes_the_score_over_100():
    assert apply_outcome(seller(95), passed=True) == (95, 100)


def test_a_failure_cuts_the_score_and_the_limit_matches_the_new_tier():
    quick = seller(31, completed=1, failed=1, limit=2500)
    assert apply_outcome(quick, passed=False) == (31, 9)
    assert quick.jobs_failed == 2
    assert quick.limit_cents == LIMITS["restricted"]


def test_a_score_never_goes_below_zero():
    assert apply_outcome(seller(5), passed=False) == (5, 0)


def test_a_failure_drops_a_trusted_seller_a_tier_straight_away():
    nova = seller(82, completed=5, limit=5000)
    apply_outcome(nova, passed=False)
    assert nova.trust_score == 60
    assert nova.limit_cents == LIMITS["building"]


def test_a_failure_with_a_low_score_restricts_a_building_seller():
    kip = seller(46, completed=2, limit=2500)
    apply_outcome(kip, passed=False)
    assert (kip.trust_score, kip.jobs_failed) == (24, 1)
    assert kip.limit_cents == LIMITS["restricted"]


def test_a_first_pass_keeps_a_new_seller_in_the_new_band():
    zed = seller(0, limit=1000)
    apply_outcome(zed, passed=True)
    assert zed.trust_score == 12
    assert zed.limit_cents == LIMITS["new"]


def test_the_numbers_match_the_mock_data_and_the_trust_ladder():
    assert PASS_BONUS == 12
    assert FAIL_PENALTY == 22
    assert LIMITS == {"new": 1000, "building": 2500, "trusted": 5000, "restricted": 500}
