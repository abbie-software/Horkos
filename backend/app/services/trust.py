# These bands match LADDER_STEPS in frontend/src/lib/trust.ts.


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