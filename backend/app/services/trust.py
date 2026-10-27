# These bands match LADDER_STEPS in frontend/src/lib/trust.ts.

PASS_BONUS = 12  # the mock data has Kip Codes going from 46 to 58
FAIL_PENALTY = 22  # and QuickPay Dev falling from 31 to 9
LIMITS = {"new": 1000, "building": 2500, "trusted": 5000, "restricted": 500}


def tier_for(trust_score: int, jobs_failed: int) -> str:
    """The seller's tier, worked out from their score and record.

    A seller with failed jobs and a score in the lowest band is Restricted:
    their limit was cut after a broken rule or failed work.
    """
    if jobs_failed > 0 and trust_score <= 25:
        return "restricted"
    if trust_score >= 75:
        return "trusted"
    if trust_score >= 26:
        return "building"
    return "new"


def apply_outcome(seller, passed: bool) -> tuple[int, int]:
    """Update a seller after a verified job. Returns (old score, new score).

    A pass raises the score a little. A failure cuts it sharply, and the
    limit follows the new tier straight away.
    """
    old = seller.trust_score
    if passed:
        seller.trust_score = min(100, old + PASS_BONUS)
        seller.jobs_completed += 1
    else:
        seller.trust_score = max(0, old - FAIL_PENALTY)
        seller.jobs_failed += 1
    seller.limit_cents = LIMITS[tier_for(seller.trust_score, seller.jobs_failed)]
    return old, seller.trust_score
