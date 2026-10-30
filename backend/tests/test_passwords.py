from app.services.passwords import (
    cached_hash,
    dummy_hash,
    hash_password,
    verify_password,
)


def test_a_password_is_stored_as_a_salted_hash_not_as_itself():
    stored = hash_password("demo-password")
    assert stored.startswith("scrypt$")
    assert "demo-password" not in stored
    assert hash_password("demo-password") != stored  # a new salt every time


def test_the_right_password_verifies_and_the_wrong_one_does_not():
    stored = hash_password("demo-password")
    assert verify_password("demo-password", stored) is True
    assert verify_password("Demo-password", stored) is False
    assert verify_password("", stored) is False


def test_anything_malformed_is_simply_a_failed_login():
    for stored in (None, "", "plaintext", "scrypt$1$2", "bcrypt$1$2$3$aa$bb", "scrypt$x$8$1$zz$zz"):
        assert verify_password("demo-password", stored) is False


def test_the_helper_hashes_are_stable_within_a_run():
    assert dummy_hash() == dummy_hash()
    assert cached_hash("demo-password") == cached_hash("demo-password")
    assert verify_password("demo-password", cached_hash("demo-password")) is True
    assert verify_password("anything", dummy_hash()) is False
