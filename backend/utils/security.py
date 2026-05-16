"""Password hashing and JWT helpers for auth (Phase 3)."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import jwt
from passlib.context import CryptContext

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Prefer env in production; dev fallback is intentionally obvious and insecure.
SECRET_KEY: str = (
    os.environ.get("RENTALAI_SECRET_KEY", "").strip()
    or os.environ.get("SECRET_KEY", "").strip()
    or "dev-insecure-change-me-set-RENTALAI_SECRET_KEY"
)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", "60") or "60"
)


def hash_password(password: str) -> str:
    """Return a bcrypt hash suitable for storing in ``User.hashed_password``."""
    return _pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a stored bcrypt hash."""
    return _pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    data: dict[str, Any],
    expires_delta: timedelta | None = None,
) -> str:
    """Encode a JWT access token with optional custom expiry."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta
        if expires_delta is not None
        else timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode["exp"] = expire
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
