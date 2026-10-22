def risk_level_for(score: int) -> str:
    """The contract's bands: low 0-33, medium 34-66, high 67-100."""
    if score <= 33:
        return "low"
    if score <= 66:
        return "medium"
    return "high"