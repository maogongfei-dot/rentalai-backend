"""
Phase 5 Round5 Step1 — Minimal in-process session token store (placeholder for future JWT/OAuth).

* Maps opaque token string → user_id (JSON persistence user id).
* Not persisted to disk; single-process demo only. No expiry / refresh in this step.
* Thread-safe for concurrent FastAPI workers is NOT guaranteed (in-memory only); use one worker for demo.

Replaceable later with: signed tokens, Redis, or DB-backed sessions.

Round5 scope: login/register issue tokens; history **read** requires Bearer; history **write** and most POST APIs
still accept body ``userId`` without Bearer binding (see README).
"""

from __future__ import annotations

import secrets
import threading
from typing import Optional

# Client-facing label for Authorization: Bearer ... (extensible).
AUTH_TYPE_SESSION_PLACEHOLDER = "session_placeholder"

_LOCK = threading.Lock()
# token_hex -> user_id
_TOKENS: dict[str, str] = {}


def issue_token(user_id: str) -> str:
    """Create a new random session token bound to ``user_id`` (does not revoke older tokens)."""
    uid = str(user_id or "").strip()
    if not uid:
        raise ValueError("user_id required")
    raw = secrets.token_hex(32)
    with _LOCK:
        _TOKENS[raw] = uid
    return raw


def revoke_token(token: str) -> None:
    """Remove token from store (e.g. logout)."""
    t = str(token or "").strip()
    if not t:
        return
    with _LOCK:
        _TOKENS.pop(t, None)


def resolve_user_id(token: str) -> Optional[str]:
    """Return user_id if token is known; else None."""
    t = str(token or "").strip()
    if not t:
        return None
    with _LOCK:
        uid = _TOKENS.get(t)
    return str(uid) if uid else None


def build_auth_payload(token: str) -> dict[str, str]:
    """Stable ``auth`` object for JSON responses."""
    return {
        "token": token,
        "auth_type": AUTH_TYPE_SESSION_PLACEHOLDER,
    }
