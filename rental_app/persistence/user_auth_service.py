"""
Phase 5 Round3 Step2 — Register / login against JSON ``UserRepository`` (server-side persistence).

* Thread-safe for single-process demo (lock around read-modify-write).
* Does not replace SQLite ``records_db`` for other features; auth endpoints use this module only.
"""

from __future__ import annotations

import threading
import uuid
from datetime import datetime, timezone
from typing import Any

from .password_hashing import hash_password, verify_password
from .user_repository import UserRepository

_REPO = UserRepository()
_LOCK = threading.Lock()


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_public_user_by_id(user_id: str) -> dict[str, Any] | None:
    """Return { user_id, email, created_at } for API responses (no secrets)."""
    uid = str(user_id or "").strip()
    if not uid:
        return None
    row = _REPO.get_by_id(uid)
    if not row:
        return None
    return {
        "user_id": str(row.get("user_id") or ""),
        "email": str(row.get("email") or ""),
        "created_at": str(row.get("created_at") or ""),
    }


def register_user(email: str, password: str) -> tuple[dict[str, Any] | None, str | None]:
    """
    Create a user in JSON store.

    Returns (public_user_dict, error_message). error_message set on failure; public_user_dict has
    user_id, email, created_at on success.
    """
    em = str(email or "").strip().lower()
    pw = str(password or "")
    if not em or not pw:
        return None, "Invalid email or password."

    with _LOCK:
        if _REPO.get_by_email(em):
            return None, "User already exists"
        uid = uuid.uuid4().hex
        now = _utc_now_iso()
        ph, algo = hash_password(pw)
        record = {
            "user_id": uid,
            "email": em,
            "password_hash": ph,
            "password_hash_algorithm": algo,
            "password_placeholder": None,
            "created_at": now,
        }
        _REPO.upsert_user(record)
    return {"user_id": uid, "email": em, "created_at": now}, None


def verify_login(email: str, password: str) -> dict[str, Any] | None:
    """Return { user_id, email, created_at } if credentials match; else None."""
    em = str(email or "").strip().lower()
    pw = str(password or "")
    if not em or not pw:
        return None
    row = _REPO.get_by_email(em)
    if not row:
        return None
    if not verify_password(
        pw,
        row.get("password_hash"),
        row.get("password_hash_algorithm"),
    ):
        return None
    return {
        "user_id": str(row.get("user_id") or ""),
        "email": str(row.get("email") or ""),
        "created_at": str(row.get("created_at") or ""),
    }
