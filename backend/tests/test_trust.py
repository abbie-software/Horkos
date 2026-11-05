from app.services.trust import tier_for


def test_score_bands_match_the_trust_ladder():
    assert tier_for(0, 0) == "new"
    assert tier_for(25, 0) == "new"
    assert tier_for(26, 0) == "building"
    assert tier_for(74, 0) == "building"
    assert tier_for(75, 0) == "trusted"
    assert tier_for(100, 0) == "trusted"


def test_failed_jobs_with_a_low_score_mean_restricted():
    assert tier_for(9, 2) == "restricted"
    assert tier_for(25, 1) == "restricted"


def test_a_failure_alone_does_not_restrict_a_building_seller():
    assert tier_for(46, 1) == "building"


def test_the_four_demo_sellers_get_the_tiers_in_the_contract():
    assert tier_for(82, 0) == "trusted"  # Nova Scripts
    assert tier_for(46, 0) == "building"  # Kip Codes
    assert tier_for(0, 0) == "new"  # Zed Dev
    assert tier_for(9, 2) == "restricted"  # QuickPay Dev