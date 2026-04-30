"""
Minimal SQLite user storage bootstrap for Phase12 Step2-2.

Scope:
- Ensure local SQLite db exists.
- Ensure `users` table exists.
- Provide stdlib `hashlib` password hashing helper.
"""

from __future__ import annotations

import hashlib
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

_ENV_USERS_DB = "RENTALAI_USERS_DB_PATH"
_DEFAULT_DB_PATH = Path(__file__).resolve().parents[1] / "rentalai_users.db"


def users_db_path() -> Path:
    override = str(os.environ.get(_ENV_USERS_DB, "")).strip()
    if override:
        return Path(override).expanduser()
    return _DEFAULT_DB_PATH


def hash_password_sha256(plain_password: str) -> str:
    """Return deterministic SHA-256 hex digest for a plain password."""
    text = str(plain_password or "")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def now_iso_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def init_users_db() -> str:
    """
    Ensure SQLite database and minimal users table exist.

    Returns the resolved db path as string.
    """
    db_path = users_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(str(db_path), timeout=5.0, check_same_thread=False) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.commit()
    return str(db_path)

