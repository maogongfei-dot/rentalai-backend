"""
Minimal SQLite user storage bootstrap for Phase12 Step2-2.

Scope:
- Ensure local SQLite db exists.
- Ensure `users` table exists.
- Provide stdlib `hashlib` password hashing helper.

Phase13 Step1-3: default SQLite filename and DATABASE_URL are centralized here.
Phase13 Step2-3: when ``DATABASE_URL`` is set, create PostgreSQL ``users`` table at startup if missing.
Phase13 Step2-4: when ``DATABASE_URL`` is set, ``find_user_by_email`` / ``create_user`` /
``verify_user_login`` use PostgreSQL; otherwise SQLite.
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

# Snapshot at import (optional introspection); runtime routing uses :func:`_active_postgres_url`.
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL is not None:
    DATABASE_URL = str(DATABASE_URL).strip() or None

_ENV_USERS_DB = "RENTALAI_USERS_DB_PATH"

_DEFAULT_DB_PATH = Path(__file__).resolve().parents[1] / DATABASE_FILENAME


def _active_postgres_url() -> str | None:
    """Return trimmed ``DATABASE_URL`` if the app should use PostgreSQL for user rows."""
    u = os.getenv("DATABASE_URL")
    if u is not None:
        u = str(u).strip() or None
    return u


def users_db_path() -> Path:
    """Resolve SQLite path for the users table.

    ``RENTALAI_USERS_DB_PATH`` overrides the default file under ``rental_app/``.
    Used when ``DATABASE_URL`` is unset (SQLite-only user storage).
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


_POSTGRES_USERS_DDL = """
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at TEXT NOT NULL
)
"""


def init_postgresql_users_table() -> bool:
    """If ``DATABASE_URL`` is set, ensure the ``users`` table exists in PostgreSQL.

    Column layout matches SQLite (``id``, ``email``, ``password_hash``, ``created_at``).

    Returns True if initialization was attempted and succeeded, False if skipped or failed.
    """
    url = _active_postgres_url()
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
            with conn.cursor() as cur:
                cur.execute(_POSTGRES_USERS_DDL)
            conn.commit()
        finally:
            try:
                conn.close()
            except Exception:
                pass
        logger.info(
            "PostgreSQL users table ensured (CREATE IF NOT EXISTS); user auth uses PG when DATABASE_URL is set."
        )
        return True
    except Exception as exc:
        logger.warning("PostgreSQL users table init failed: %s", exc)
        return False


def _find_user_by_email_sqlite(em: str) -> dict[str, str] | None:
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


def _find_user_by_email_postgres(url: str, em: str) -> dict[str, str] | None:
    import psycopg2

    conn = psycopg2.connect(url)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, email, password_hash, created_at FROM users WHERE email = %s LIMIT 1",
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
    finally:
        try:
            conn.close()
        except Exception:
            pass


def find_user_by_email(email: str) -> dict[str, str] | None:
    em = str(email or "").strip().lower()
    if not em:
        return None
    url = _active_postgres_url()
    if url:
        return _find_user_by_email_postgres(url, em)
    return _find_user_by_email_sqlite(em)


def create_user(email: str, password: str) -> tuple[dict[str, str] | None, str | None]:
    """
    Insert a new user (PostgreSQL when ``DATABASE_URL`` is set, else SQLite).

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

    url = _active_postgres_url()
    if url:
        return _insert_user_postgres(url, user_id, em, password_hash, created_at)

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


def _insert_user_postgres(
    url: str,
    user_id: str,
    em: str,
    password_hash: str,
    created_at: str,
) -> tuple[dict[str, str] | None, str | None]:
    import psycopg2

    conn = psycopg2.connect(url)
    try:
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO users (id, email, password_hash, created_at)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (user_id, em, password_hash, created_at),
                )
            conn.commit()
        except psycopg2.IntegrityError:
            conn.rollback()
            return None, "Email already registered"
    finally:
        try:
            conn.close()
        except Exception:
            pass

    return {
        "id": user_id,
        "email": em,
        "password_hash": password_hash,
        "created_at": created_at,
    }, None


def verify_user_login(email: str, password: str) -> tuple[dict[str, str] | None, str | None]:
    """
    Validate login credentials (PostgreSQL when ``DATABASE_URL`` is set, else SQLite).

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

