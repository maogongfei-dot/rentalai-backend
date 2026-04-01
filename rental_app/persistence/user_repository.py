"""
Repository over ``user_store`` — read-oriented skeleton; write helpers reserved for later auth wiring.

UserRecord (JSON object) fields::

    user_id: str
    email: str (normalized lowercase for lookup)
    password_hash: str | null — set when hashing is implemented; null = not stored here yet
    password_placeholder: str | null — reserved for migration/dev flags (e.g. \"pending\")
    created_at: str — ISO8601 UTC
"""

from __future__ import annotations

from typing import Any

from . import user_store


def _norm_email(email: str) -> str:
    return (email or "").strip().lower()


class UserRepository:
    """Formal-style accessor for JSON-backed users (Phase 5 Round3 skeleton)."""

    def load_document(self) -> dict[str, Any]:
        return user_store.load_users_document()

    def save_document(self, doc: dict[str, Any]) -> None:
        user_store.save_users_document(doc)

    def get_by_id(self, user_id: str) -> dict[str, Any] | None:
        uid = str(user_id or "").strip()
        if not uid:
            return None
        doc = self.load_document()
        users = doc.get("users") or {}
        row = users.get(uid)
        return dict(row) if isinstance(row, dict) else None

    def get_by_email(self, email: str) -> dict[str, Any] | None:
        em = _norm_email(email)
        if not em:
            return None
        doc = self.load_document()
        for row in (doc.get("users") or {}).values():
            if not isinstance(row, dict):
                continue
            if _norm_email(str(row.get("email") or "")) == em:
                return dict(row)
        return None

    def list_user_ids(self) -> list[str]:
        doc = self.load_document()
        users = doc.get("users") or {}
        return sorted(str(k) for k in users.keys() if k)

    def upsert_user(self, record: dict[str, Any]) -> None:
        """Minimal write path for future migration tests (keeps schema_version)."""
        uid = str(record.get("user_id") or "").strip()
        if not uid:
            raise ValueError("user_id is required")
        doc = self.load_document()
        users = dict(doc.get("users") or {})
        users[uid] = dict(record)
        doc["users"] = users
        user_store.save_users_document(doc)
