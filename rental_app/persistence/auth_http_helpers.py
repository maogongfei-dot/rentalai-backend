"""
Phase 5 Round5 Step3 — HTTP auth helpers for protected routes (minimal; not global middleware).

* ``Authorization: Bearer <token>`` → ``resolve_user_id`` via ``auth_session_store``.
* Use on selected endpoints only (e.g. analysis history read).
"""

from __future__ import annotations

from typing import Optional

from fastapi import Request

from .auth_session_store import resolve_user_id


def extract_bearer_token(request: Request) -> Optional[str]:
    """Raw bearer token from ``Authorization`` header, or None."""
    auth = request.headers.get("Authorization") or ""
    if not auth.startswith("Bearer "):
        return None
    token = auth[len("Bearer ") :].strip()
    return token or None


def resolve_user_id_from_auth_header(request: Request) -> Optional[str]:
    """
    Map ``Authorization: Bearer`` to persisted user id (session placeholder store).

    Alias intent: same as ``get_current_user_id_from_auth`` / ``resolve_user_from_token``
    for this project's minimal token store.
    """
    token = extract_bearer_token(request)
    if not token:
        return None
    return resolve_user_id(token)


def get_current_user_id_from_auth(request: Request) -> Optional[str]:
    """Same as :func:`resolve_user_id_from_auth_header`."""
    return resolve_user_id_from_auth_header(request)
