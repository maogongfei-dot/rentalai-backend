"""
Minimal SQLite user storage bootstrap for Phase12 Step2-2.

Scope:
- Ensure local SQLite db exists.
- Ensure `users` table exists.
- Provide stdlib `hashlib` password hashing helper.

Phase13 Step1-3: default SQLite filename and DATABASE_URL are centralized here.
Phase13 Step2-2: if ``DATABASE_URL`` is set, startup probes PostgreSQL with ``psycopg2``;
``/register`` / ``/login`` still use SQLite only until a later migration step.
"""

from __future__ import annotations

import hashlib
import logging
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

# --- Phase13: user database configuration (SQLite remains the default store for users) ---

# Default SQLite file name under ``rental_app/`` (same folder as the parent of ``persistence/``).
DATABASE_FILENAME = "rentalai_users.db"

# PostgreSQL URL when present (e.g. Render). User CRUD still uses SQLite; probe-only until migration.
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL is not None:
    DATABASE_URL = str(DATABASE_URL).strip() or None

_ENV_USERS_DB = "RENTALAI_USERS_DB_PATH"

_DEFAULT_DB_PATH = Path(__file__).resolve().parents[1] / DATABASE_FILENAME


def users_db_path() -> Path:
    """Resolve SQLite path for the users table.

    ``RENTALAI_USERS_DB_PATH`` overrides the default file under ``rental_app/``.
    ``DATABASE_URL`` does not change this path: register/login still read/write SQLite here
    until user rows are migrated to PostgreSQL.
    """
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


def probe_postgresql_connection() -> bool:
    """If ``DATABASE_URL`` is set, open and close a PostgreSQL connection (connectivity check only).

    Does not create tables or change how ``find_user_by_email`` / ``create_user`` work (still SQLite).
    Returns True if a probe was attempted and succeeded, False if skipped or failed.
    """
    url = os.getenv("DATABASE_URL")
    if url is not None:
        url = str(url).strip() or None
    if not url:
        return False
    try:
        import psycopg2
    except ImportError as exc:
        logger.warning("DATABASE_URL is set but psycopg2 is not importable: %s", exc)
        return False
    try:
        conn = psycopg2.connect(url)
        try:
            conn.close()
        except Exception:
            pass
        logger.info("PostgreSQL connection probe succeeded (user storage remains SQLite).")
        return True
    except Exception as exc:
        logger.warning("PostgreSQL connection probe failed: %s", exc)
        return False


def find_user_by_email(email: str) -> dict[str, str] | None:
    em = str(email or "").strip().lower()
    if not em:
        return None
    db_path = users_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(str(db_path), timeout=5.0, check_same_thread=False) as conn:
        cur = conn.execute(
            "SELECT id, email, password_hash, created_at FROM users WHERE email = ? LIMIT 1",
            (em,),
        )
        row = cur.fetchone()
        if row is None:
            return None
        return {
            "id": str(row[0] or ""),
            "email": str(row[1] or ""),
            "password_hash": str(row[2] or ""),
            "created_at": str(row[3] or ""),
        }


def create_user(email: str, password: str) -> tuple[dict[str, str] | None, str | None]:
    """
    Insert a new user into SQLite users table.

    Returns (user_row, error_message).
    """
    em = str(email or "").strip().lower()
    pw = str(password or "")
    if not em or not pw:
        return None, "Email and password cannot be empty"
    if find_user_by_email(em):
        return None, "Email already registered"

    user_id = uuid.uuid4().hex
    created_at = now_iso_utc()
    password_hash = hash_password_sha256(pw)
    db_path = users_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with sqlite3.connect(str(db_path), timeout=5.0, check_same_thread=False) as conn:
            conn.execute(
                """
                INSERT INTO users (id, email, password_hash, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (user_id, em, password_hash, created_at),
            )
            conn.commit()
    except sqlite3.IntegrityError:
        return None, "Email already registered"

    return {
        "id": user_id,
        "email": em,
        "password_hash": password_hash,
        "created_at": created_at,
    }, None


def verify_user_login(email: str, password: str) -> tuple[dict[str, str] | None, str | None]:
    """
    Validate login credentials against SQLite users table.

    Returns (public_user, error_message).
    """
    em = str(email or "").strip().lower()
    pw = str(password or "")
    if not em or not pw:
        return None, "Email and password cannot be empty"

    user = find_user_by_email(em)
    if user is None:
        return None, "User not found"

    provided_hash = hash_password_sha256(pw)
    if provided_hash != str(user.get("password_hash") or ""):
        return None, "Incorrect password"

    return {
        "id": str(user.get("id") or ""),
        "email": str(user.get("email") or ""),
    }, None

