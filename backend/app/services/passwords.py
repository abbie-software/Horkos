import hashlib
import hmac
import os
from functools import lru_cache

# scrypt is in Python's standard library, so there is nothing extra to install.
N, R, P = 2**14, 8, 1


def hash_password(password: str) -> str:
    """A salted hash, stored as scrypt$n$r$p$salt$hash. The password itself is never kept."""
    salt = os.urandom(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=N, r=R, p=P)
    return f"scrypt${N}${R}${P}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str | None) -> bool:
    """True only if the password matches. Anything malformed is simply False."""
    try:
        scheme, n, r, p, salt_hex, digest_hex = (stored or "").split("$")
        if scheme != "scrypt":
            return False
        expected = bytes.fromhex(digest_hex)
        actual = hashlib.scrypt(
            password.encode(),
            salt=bytes.fromhex(salt_hex),
            n=int(n),
            r=int(r),
            p=int(p),
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(actual, expected)


@lru_cache(maxsize=1)
def dummy_hash() -> str:
    """Checked when the email is unknown, so a wrong email takes as long as a wrong password."""
    return hash_password("not-a-real-password")


@lru_cache(maxsize=4)
def cached_hash(password: str) -> str:
    """Hash a fixed password once per run. Used by the demo seed, which runs often."""
    return hash_password(password)
