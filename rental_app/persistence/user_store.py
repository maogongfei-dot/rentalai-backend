"""
Phase 5 Round3 Step1 — User rows persisted as JSON (formal backend shape, not wired to /auth yet).

On-disk document::
    {
      "schema_version": 1,
      "users": {
        "<user_id>": { ... UserRecord ... }
      }
    }

This layer is independent of ``data.storage.records_db`` (SQLite). Existing auth flows stay unchanged
until explicitly migrated in a later step.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from .json_io import load_json_object, save_json_atomic

SCHEMA_VERSION = 1

_ENV_USERS_JSON = "RENTALAI_PERSISTENCE_USERS_JSON"


def default_users_json_path() -> Path:
    base = Path(__file__).resolve().parents[1] / "data" / "storage"
    return base / "persistence_users.json"


def users_json_path() -> Path:
    override = os.environ.get(_ENV_USERS_JSON, "").strip()
    if override:
        return Path(override).expanduser()
    return default_users_json_path()


def empty_users_document() -> dict[str, Any]:
    return {"schema_version": SCHEMA_VERSION, "users": {}}


def load_users_document() -> dict[str, Any]:
    doc = load_json_object(users_json_path(), empty_users_document())
    if doc.get("schema_version") != SCHEMA_VERSION:
        # Future migrations can branch here; for now accept and normalize
        doc.setdefault("schema_version", SCHEMA_VERSION)
    users = doc.get("users")
    if not isinstance(users, dict):
        doc["users"] = {}
    return doc


def save_users_document(doc: dict[str, Any]) -> None:
    doc = dict(doc)
    doc["schema_version"] = SCHEMA_VERSION
    if not isinstance(doc.get("users"), dict):
        doc["users"] = {}
    save_json_atomic(users_json_path(), doc)
