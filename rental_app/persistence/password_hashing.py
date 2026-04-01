"""
Password hashing helpers for JSON user store.

* Current: ``sha256_v1`` — SHA-256 hex of UTF-8 password (same idea as ``records_db._password_hash``).
* Future: add e.g. ``bcrypt_v1`` and branch in ``verify_password`` without changing stored user shape
  (``password_hash`` + ``password_hash_algorithm``).
"""

from __future__ import annotations

import hashlib
from typing import Any

ALGO_SHA256_V1 = "sha256_v1"


def hash_password(plain: str) -> tuple[str, str]:
    """Return (hex_digest, algorithm_id)."""
    p = str(plain or "")
    digest = hashlib.sha256(p.encode("utf-8")).hexdigest()
    return digest, ALGO_SHA256_V1


def verify_password(plain: str, stored_hash: Any, algorithm: Any) -> bool:
    if stored_hash is None or stored_hash == "":
        return False
    algo = str(algorithm or "").strip() or ALGO_SHA256_V1
    if algo == ALGO_SHA256_V1:
        return hash_password(plain)[0] == str(stored_hash)
    # Unknown algorithm: fail closed until explicit support is added
    return False
