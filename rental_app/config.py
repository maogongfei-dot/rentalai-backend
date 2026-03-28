"""Phase4 — minimal runtime configuration from environment (no secrets in code).

SQLite path and task store paths are still read inside their owning modules; set the
corresponding env vars before any import of `api_server` if you override defaults.
"""

from __future__ import annotations

import os
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parent

# Optional signing / future use (in-memory tokens do not use this yet).
SECRET_KEY: str = os.environ.get("RENTALAI_SECRET_KEY", "").strip()

DEBUG: bool = os.environ.get("RENTALAI_DEBUG", "").strip().lower() in (
    "1",
    "true",
    "yes",
)


def get_bind_host() -> str:
    explicit = (os.environ.get("RENTALAI_HOST") or "").strip()
    if explicit:
        return explicit
    # Common PaaS pattern: PORT set without explicit host → listen on all interfaces.
    if (os.environ.get("PORT") or "").strip():
        return "0.0.0.0"
    return "127.0.0.1"


def get_bind_port() -> int:
    for key in ("RENTALAI_PORT", "PORT"):
        raw = (os.environ.get(key) or "").strip()
        if raw.isdigit():
            p = int(raw)
            if 1 <= p <= 65535:
                return p
    return 8000


def get_uvicorn_reload() -> bool:
    return os.environ.get("RENTALAI_RELOAD", "").strip().lower() in ("1", "true", "yes")


def _cors_default_origins() -> list[str]:
    """Extra origins merged when ALLOWED_ORIGINS is a non-empty explicit list.

    Covers local dev and common Render hostnames so a partial ALLOWED_ORIGINS (e.g. only Vercel)
    does not block the Render-hosted UI or same-service hostname.
    """
    return [
        "http://127.0.0.1:8000",
        "http://localhost:8000",
        "http://localhost:5173",
        "http://localhost:3000",
        "https://rentalai-backend.onrender.com",
    ]


def get_cors_origins() -> tuple[list[str], bool]:
    """CORS allow_origins and whether credentials may be sent.

    - **ALLOWED_ORIGINS** unset or empty: ``["*"]`` (open; no credentials).
    - Comma-separated explicit origins: those hosts only, credentials on; by default we **merge**
      :func:`_cors_default_origins` unless **ALLOWED_ORIGINS_STRICT=1**.
    - If ``*`` appears in the list, wildcard wins (credentials off).
    """
    raw = (os.environ.get("ALLOWED_ORIGINS") or "").strip()
    if not raw:
        return (["*"], False)
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    if not parts:
        return (["*"], False)
    if any(p == "*" for p in parts):
        return (["*"], False)
    strict = os.environ.get("ALLOWED_ORIGINS_STRICT", "").strip().lower() in (
        "1",
        "true",
        "yes",
    )
    if not strict:
        for d in _cors_default_origins():
            if d not in parts:
                parts.append(d)
        extra = (os.environ.get("RENTALAI_EXTRA_ALLOWED_ORIGINS") or "").strip()
        for p in extra.split(","):
            p = p.strip()
            if p and p not in parts:
                parts.append(p)
    return (parts, True)
