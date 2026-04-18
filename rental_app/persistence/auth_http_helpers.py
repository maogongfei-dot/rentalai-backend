"""
Phase 5 Round5 Step3/5 — HTTP auth helpers for protected routes (minimal; not global middleware).

* ``Authorization: Bearer <token>`` → ``resolve_user_id`` via ``auth_session_store`` (session placeholder, not JWT).
* Used by: ``GET /api/analysis/history/records`` (read); ``resolve_history_write_user_id`` (Phase 5 Round 6) for JSON history **append** on analysis routes.
* Not done here: JWT, expiry, refresh, full-route middleware — see ``persistence/README.md``「最小受保护 API」.
"""

from __future__ import annotations

from typing import Any, Optional

import re

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


def _resolve_guest_history_user_id(request: Request) -> str:
    """
    历史写入逻辑（游客）：
    - 不登录时，不再写入全局固定 guest
    - 改为优先读取 X-Guest-Session
    - 若格式合法，则写入 guest:<session>
    - 若没有可用游客会话，则回退到 guest:anonymous

    这样可以做到：
    1）不同游客之间历史隔离
    2）登录用户历史与游客历史天然分开
    3）登录后不会读取游客历史（后续读取仍以 Bearer user_id 为准）
    """
    raw = (request.headers.get("X-Guest-Session") or "").strip()
    if raw and re.fullmatch(r"[a-fA-F0-9\\-]{8,128}", raw):
        compact = raw.replace("-", "")[:48]
        return "guest:" + compact
    return "guest:anonymous"


def resolve_history_read_user_id(request: Request) -> str:
    """
    历史读取逻辑：
    - 登录用户：严格读取 Bearer token 对应的真实 user_id
    - 游客：读取当前游客会话桶 guest:<session>
    - 若没有可用游客会话，则回退到 guest:anonymous

    这样可以保证：
    1）每个用户只能看到自己的历史
    2）游客历史与登录用户历史分开
    3）登录后不会读取游客历史
    """
    uid_auth = resolve_user_id_from_auth_header(request)
    if uid_auth:
        return uid_auth
    return _resolve_guest_history_user_id(request)


def resolve_history_write_user_id(request: Request, body: Any) -> dict[str, Any]:
    """
    Decide whether server-side JSON history may be appended, and as which user.

    用户绑定逻辑：
    * **Bearer 存在**：历史写入严格绑定 token 解析出的真实 user_id；
      body 里的 ``userId`` / ``user_id`` 只做校验，不能单独作为身份来源。
    * **无 Bearer**：历史写入走游客隔离桶；
      优先使用 ``X-Guest-Session`` 生成 ``guest:<session>``，
      若没有可用游客会话，则回退为 ``guest:anonymous``。
    * 登录用户与游客历史分开；登录后读取历史仍以 Bearer 用户为准，不合并游客历史。

    Returns ``{ "ok": bool, "user_id": str | None, "message": str | None }``.
    ``ok`` False means do not append; ``message`` is safe for API JSON.
    """
    from .analysis_history_writer import resolve_history_user_id

    claimed = resolve_history_user_id(body)
    uid_auth = resolve_user_id_from_auth_header(request)

    if uid_auth:
        if claimed != "guest" and claimed != uid_auth:
            return {
                "ok": False,
                "user_id": None,
                "message": "userId does not match authenticated user.",
            }
        return {"ok": True, "user_id": uid_auth, "message": None}

    if claimed != "guest":
        return {
            "ok": False,
            "user_id": None,
            "message": "Authentication required. Send Authorization: Bearer <token> to write server-side history.",
        }

    guest_user_id = _resolve_guest_history_user_id(request)
    return {"ok": True, "user_id": guest_user_id, "message": None}
