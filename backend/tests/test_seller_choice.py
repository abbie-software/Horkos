from types import SimpleNamespace

from app.services.seller_choice import pick_seller


def seller(id, trust, limit):
    return SimpleNamespace(id=id, trust_score=trust, limit_cents=limit)


SELLERS = [seller(1, 82, 5000), seller(2, 46, 2500), seller(3, 0, 1000), seller(4, 9, 500)]


def test_the_most_trusted_seller_whose_limit_covers_the_price_wins():
    assert pick_seller(SELLERS, 2000).id == 1
    assert pick_seller(SELLERS, 500).id == 1


def test_a_seller_whose_limit_is_too_low_is_skipped():
    sellers = [seller(1, 30, 1000), seller(2, 20, 5000)]
    assert pick_seller(sellers, 3000).id == 2


def test_if_nobody_covers_the_price_the_most_trusted_seller_is_chosen():
    assert pick_seller(SELLERS, 9000).id == 1


def test_ties_go_to_the_lowest_id_and_an_empty_list_is_an_error():
    assert pick_seller([seller(5, 50, 5000), seller(3, 50, 5000)], 1000).id == 3
    try:
        pick_seller([], 1000)
    except ValueError:
        return
    raise AssertionError("expected ValueError")