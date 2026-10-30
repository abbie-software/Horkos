from datetime import UTC, datetime, timedelta

import jwt

from app.config import settings
from app.errors import ApiError
from app.services.tokens import issue_token, read_token

SECRET = "a-long-secret-for-the-tests-0123456789"


class WithSecret:
    """Sets the signing secret for one block, then puts it back."""

    def __init__(self, value):
        self.value = value

    def __enter__(self):
        self.previous = settings.jwt_secret
        settings.jwt_secret = self.value

    def __exit__(self, *args):
        settings.jwt_secret = self.previous


def refused(token, expect=None):
    try:
        read_token(token)
    except ApiError as exc:
        assert exc.status_code == 401
        assert exc.code == "unauthorized"
        assert expect is None or expect in exc.message
        return True
    return False


def test_a_token_carries_the_user_id_and_comes_back_the_same():
    with WithSecret(SECRET):
        assert read_token(issue_token(42)) == 42


def test_a_token_signed_with_another_secret_is_refused():
    with WithSecret("some-other-secret-0123456789abcdef"):
        foreign = issue_token(1)
    with WithSecret(SECRET):
        assert refused(foreign, "Invalid token")


def test_an_expired_token_says_so():
    with WithSecret(SECRET):
        old = issue_token(1, now=datetime.now(UTC) - timedelta(days=2))
        assert refused(old, "expired")


def test_garbage_is_refused():
    with WithSecret(SECRET):
        for junk in ("", "garbage", "a.b.c", "Bearer abc"):
            assert refused(junk, "Invalid token")


def test_a_token_that_claims_no_signature_is_refused():
    with WithSecret(SECRET):
        claims = {"sub": "1", "exp": datetime.now(UTC) + timedelta(hours=1)}
        unsigned = jwt.encode(claims, "", algorithm="none")
        assert refused(unsigned, "Invalid token")


def test_a_token_without_an_expiry_or_with_a_strange_subject_is_refused():
    with WithSecret(SECRET):
        no_expiry = jwt.encode({"sub": "1"}, SECRET, algorithm="HS256")
        assert refused(no_expiry)
        future = datetime.now(UTC) + timedelta(hours=1)
        odd_subject = jwt.encode({"sub": "abc", "exp": future}, SECRET, algorithm="HS256")
        assert refused(odd_subject, "Invalid token")


def test_without_a_real_secret_nobody_can_log_in():
    for weak in ("", "short"):
        with WithSecret(weak):
            try:
                issue_token(1)
            except ApiError as exc:
                assert exc.status_code == 500
                assert "JWT_SECRET" in exc.message
            else:
                raise AssertionError("a token was issued without a real secret")
