"""
Phase 5 Step3 — 最小占位 auth（进程内内存，无持久化、非生产安全）。
与现有 /auth/register、/auth/login（SQLite + Bearer）并行，仅用于统一前后端响应形状。
"""

from __future__ import annotations

import threading
import uuid
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

_MINIMAL_LOCK = threading.Lock()
# key: email 规范化小写 -> { userId, email, password_plain }
_MINIMAL_USERS: dict[str, dict[str, str]] = {}


class MinimalAuthBody(BaseModel):
    model_config = ConfigDict(extra="ignore")

    email: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


def _norm_email(raw: str) -> str:
    return (raw or "").strip().lower()


def minimal_register_response(body: MinimalAuthBody) -> tuple[dict[str, Any], int]:
    em = _norm_email(body.email)
    pw = str(body.password or "")
    if not em or not pw:
        return (
            {
                "success": False,
                "user": None,
                "message": "email and password are required",
            },
            400,
        )
    with _MINIMAL_LOCK:
        if em in _MINIMAL_USERS:
            return (
                {
                    "success": False,
                    "user": None,
                    "message": "email already registered (minimal mock)",
                },
                409,
            )
        uid = "mu_" + uuid.uuid4().hex[:16]
        _MINIMAL_USERS[em] = {
            "userId": uid,
            "email": em,
            "password_plain": pw,
        }
    return (
        {
            "success": True,
            "user": {"userId": uid, "email": em},
            "message": "registered (minimal mock, in-memory only)",
        },
        200,
    )


def minimal_login_response(body: MinimalAuthBody) -> tuple[dict[str, Any], int]:
    em = _norm_email(body.email)
    pw = str(body.password or "")
    if not em or not pw:
        return (
            {
                "success": False,
                "user": None,
                "message": "email and password are required",
            },
            400,
        )
    with _MINIMAL_LOCK:
        row = _MINIMAL_USERS.get(em)
        if row is None or row.get("password_plain") != pw:
            return (
                {
                    "success": False,
                    "user": None,
                    "message": "invalid email or password (minimal mock)",
                },
                401,
            )
        uid = row["userId"]
        email_out = row["email"]
    return (
        {
            "success": True,
            "user": {"userId": uid, "email": email_out},
            "message": "logged in (minimal mock, no token issued)",
        },
        200,
    )
