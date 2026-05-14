"""Password hashing and verification using PBKDF2-HMAC-SHA256.

Stdlib-only so we avoid pulling a new dependency for an MVP. Format::

    pbkdf2_sha256$<iterations>$<salt_b64>$<hash_b64>

``hash_password`` generates a fresh salt; ``verify_password`` is
constant-time and tolerates unknown formats by returning ``False``.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import secrets

ALGORITHM = "pbkdf2_sha256"
DEFAULT_ITERATIONS = 240_000
SALT_BYTES = 16
HASH_BYTES = 32


class InvalidPasswordHashError(ValueError):
    """Raised when an encoded hash cannot be parsed."""


def _b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def hash_password(password: str, *, iterations: int = DEFAULT_ITERATIONS) -> str:
    if not isinstance(password, str) or password == "":
        raise ValueError("password must be a non-empty string.")
    if iterations < 1000:
        raise ValueError("iterations must be at least 1000.")

    salt = secrets.token_bytes(SALT_BYTES)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        iterations,
        dklen=HASH_BYTES,
    )
    return f"{ALGORITHM}${iterations}${_b64encode(salt)}${_b64encode(digest)}"


def verify_password(password: str, encoded: str) -> bool:
    if not isinstance(password, str) or not isinstance(encoded, str):
        return False

    try:
        algorithm, iterations_str, salt_b64, hash_b64 = encoded.split("$", 3)
    except ValueError:
        return False
    if algorithm != ALGORITHM:
        return False
    try:
        iterations = int(iterations_str)
    except ValueError:
        return False
    if iterations < 1:
        return False

    try:
        salt = _b64decode(salt_b64)
        expected = _b64decode(hash_b64)
    except (ValueError, base64.binascii.Error):  # type: ignore[attr-defined]
        return False

    actual = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        iterations,
        dklen=len(expected),
    )
    return hmac.compare_digest(actual, expected)
