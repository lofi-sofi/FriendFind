"""Password hashing (Argon2) and signed tokens for email links."""
from __future__ import annotations

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHashError
from flask import current_app
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

_ph = PasswordHasher()


def hash_password(password: str) -> str:
    return _ph.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _ph.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def _serializer(salt: str) -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt=salt)


def make_token(payload, salt: str) -> str:
    return _serializer(salt).dumps(payload)


def read_token(token: str, salt: str, max_age: int | None = None):
    """Return the payload, or None if the token is invalid/expired."""
    try:
        return _serializer(salt).loads(token, max_age=max_age)
    except (BadSignature, SignatureExpired):
        return None


# Salts (namespaces) for the different token kinds.
SALT_VERIFY_EMAIL = "verify-email"
SALT_UNSUBSCRIBE = "unsubscribe"
