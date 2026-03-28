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


def get_cors_origins() -> tuple[list[str], bool]:
    """CORS allow_origins and whether credentials may be sent.

    - **ALLOWED_ORIGINS** unset or empty: ``["*"]`` (dev-friendly; same as legacy behavior).
    - Comma-separated explicit origins (e.g. ``https://app.vercel.app``): list those;
      ``allow_credentials`` is True only for explicit non-wildcard lists.
    - If ``*`` appears with other entries, wildcard wins (credentials off).
    """
    raw = (os.environ.get("ALLOWED_ORIGINS") or "").strip()
    if not raw:
        return (["*"], False)
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    if not parts:
        return (["*"], False)
    if any(p == "*" for p in parts):
        return (["*"], False)
    return (parts, True)
