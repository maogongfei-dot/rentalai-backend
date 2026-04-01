"""
Phase 5 Round5 Step3/5 — HTTP auth helpers for protected routes (minimal; not global middleware).

* ``Authorization: Bearer <token>`` → ``resolve_user_id`` via ``auth_session_store`` (session placeholder, not JWT).
* Used by: ``GET /api/analysis/history/records`` (read); ``resolve_history_write_user_id`` (Phase 6) for JSON history **append** on analysis routes.
* Not done here: JWT, expiry, refresh, full-route middleware — see ``persistence/README.md``「最小受保护 API」.
"""

from __future__ import annotations

from typing import Any, Optional

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


def resolve_history_write_user_id(request: Request, body: Any) -> dict[str, Any]:
    """
    Decide whether server-side JSON history may be appended, and as which user.

    * Body ``userId`` / ``user_id`` from :func:`analysis_history_writer.resolve_history_user_id` (**claimed**).
    * **guest** bucket: no Bearer required; append as ``guest``.
    * **non-guest** claimed id: requires ``Authorization: Bearer``; token must resolve to the **same** user id
      (token is source of truth; body must match).

    Returns ``{ "ok": bool, "user_id": str | None, "message": str | None }``.
    ``ok`` False means do not append; ``message`` is safe for API JSON.
    """
    from .analysis_history_writer import resolve_history_user_id

    claimed = resolve_history_user_id(body)
    if claimed == "guest":
        return {"ok": True, "user_id": "guest", "message": None}
    uid_auth = resolve_user_id_from_auth_header(request)
    if not uid_auth:
        return {
            "ok": False,
            "user_id": None,
            "message": "Authentication required. Send Authorization: Bearer <token> to write server-side history.",
        }
    if uid_auth != claimed:
        return {
            "ok": False,
            "user_id": None,
            "message": "userId does not match authenticated user.",
        }
    return {"ok": True, "user_id": uid_auth, "message": None}
