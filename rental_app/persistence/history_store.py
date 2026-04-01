"""
Phase 5 Round3 — Server-side analysis history as JSON (formal shape; Step3 写入 / Step4 读取).

Document::
    { "schema_version": 1, "records": [ { ... }, ... ] }

Path: ``data/storage/persistence_analysis_history.json`` or ``RENTALAI_PERSISTENCE_ANALYSIS_HISTORY_JSON``.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from .json_io import load_json_object, save_json_atomic

SCHEMA_VERSION = 1

_ENV_HISTORY_JSON = "RENTALAI_PERSISTENCE_ANALYSIS_HISTORY_JSON"


def default_history_json_path() -> Path:
    base = Path(__file__).resolve().parents[1] / "data" / "storage"
    return base / "persistence_analysis_history.json"


def history_json_path() -> Path:
    override = os.environ.get(_ENV_HISTORY_JSON, "").strip()
    if override:
        return Path(override).expanduser()
    return default_history_json_path()


def empty_history_document() -> dict[str, Any]:
    return {"schema_version": SCHEMA_VERSION, "records": []}


def load_history_document() -> dict[str, Any]:
    doc = load_json_object(history_json_path(), empty_history_document())
    doc.setdefault("schema_version", SCHEMA_VERSION)
    recs = doc.get("records")
    if not isinstance(recs, list):
        doc["records"] = []
    return doc


def save_history_document(doc: dict[str, Any]) -> None:
    doc = dict(doc)
    doc["schema_version"] = SCHEMA_VERSION
    if not isinstance(doc.get("records"), list):
        doc["records"] = []
    save_json_atomic(history_json_path(), doc)
