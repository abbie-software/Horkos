def pick_seller(sellers, amount_cents: int):
    """Pick the seller for a job when the user did not name one.

    The most trusted seller whose limit covers the price wins. If nobody's
    limit covers it, the most trusted seller overall is chosen, and the Guard
    will then ask the user. Ties go to the lowest ID, so the choice is stable.
    """
    sellers = list(sellers)
    if not sellers:
        raise ValueError("There are no sellers to choose from")
    covering = [s for s in sellers if s.limit_cents >= amount_cents]
    pool = covering or sellers
    return max(pool, key=lambda s: (s.trust_score, -s.id))