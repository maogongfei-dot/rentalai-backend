"""Password hashing for auth (Phase 3). Uses bcrypt via passlib."""

from __future__ import annotations

from passlib.context import CryptContext

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Return a bcrypt hash suitable for storing in ``User.hashed_password``."""
    return _pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a stored bcrypt hash."""
    return _pwd_context.verify(plain_password, hashed_password)
