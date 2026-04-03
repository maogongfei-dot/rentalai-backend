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


def get_env_profile() -> str:
    """Local dev vs deploy: ``development`` | ``production``.

    Set ``RENTALAI_ENV=production`` on PaaS; omit or ``development`` for local.
    """
    raw = (os.environ.get("RENTALAI_ENV") or "").strip().lower()
    if raw in ("production", "prod"):
        return "production"
    if raw in ("development", "dev"):
        return "development"
    return "development"


def is_production_profile() -> bool:
    return get_env_profile() == "production"


def get_effective_debug() -> bool:
    """Never treat production profile as debug unless ``RENTALAI_DEBUG`` forces it."""
    if is_production_profile() and (os.environ.get("RENTALAI_DEBUG") or "").strip() == "":
        return False
    return DEBUG


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


def get_default_api_url_for_tools() -> str:
    """Default FastAPI base URL for Streamlit / CLI when ``RENTALAI_API_URL`` is unset.

    Uses ``RENTALAI_PUBLIC_API_HOST`` (default ``127.0.0.1``) and the same port as
    :func:`get_bind_port` so changing ``RENTALAI_PORT`` keeps defaults aligned.
    """
    explicit = (os.environ.get("RENTALAI_API_URL") or "").strip()
    if explicit:
        return explicit.rstrip("/")
    host = (os.environ.get("RENTALAI_PUBLIC_API_HOST") or "127.0.0.1").strip() or "127.0.0.1"
    return "http://%s:%s" % (host, get_bind_port())


def get_uvicorn_reload() -> bool:
    explicit = (os.environ.get("RENTALAI_RELOAD") or "").strip().lower()
    if explicit in ("1", "true", "yes"):
        return True
    if explicit in ("0", "false", "no"):
        return False
    if is_production_profile():
        return False
    return False


def _cors_default_origins() -> list[str]:
    """Extra origins merged when ALLOWED_ORIGINS is a non-empty explicit list.

    Covers local dev and common Render hostnames so a partial ALLOWED_ORIGINS (e.g. only Vercel)
    does not block the Render-hosted UI or same-service hostname.
    """
    port = get_bind_port()
    return [
        "http://127.0.0.1:%s" % port,
        "http://localhost:%s" % port,
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
