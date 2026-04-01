"""
Repository over ``history_store`` — append/list for server-side analysis history.
"""

from __future__ import annotations

import threading
from typing import Any

from . import history_store

_LOCK = threading.Lock()


class HistoryRepository:
    """JSON-backed analysis history (Phase 5 Round3)."""

    def load_document(self) -> dict[str, Any]:
        return history_store.load_history_document()

    def save_document(self, doc: dict[str, Any]) -> None:
        history_store.save_history_document(doc)

    def append_record(self, record: dict[str, Any]) -> None:
        rid = str(record.get("record_id") or "").strip()
        if not rid:
            raise ValueError("record_id is required")
        with _LOCK:
            doc = self.load_document()
            records = [r for r in (doc.get("records") or []) if isinstance(r, dict) and str(r.get("record_id")) != rid]
            records.append(dict(record))
            doc["records"] = records
            self.save_document(doc)

    def list_by_user(
        self,
        user_id: str,
        limit: int = 100,
        *,
        record_type: str | None = None,
    ) -> list[dict[str, Any]]:
        uid = str(user_id or "").strip()
        if not uid:
            return []
        want_type: str | None = None
        if record_type is not None and str(record_type).strip():
            want_type = str(record_type).strip().lower()
        doc = self.load_document()
        out: list[dict[str, Any]] = []
        for row in doc.get("records") or []:
            if not isinstance(row, dict):
                continue
            if str(row.get("userId") or "").strip() != uid:
                continue
            if want_type is not None:
                if str(row.get("type") or "").strip().lower() != want_type:
                    continue
            out.append(dict(row))
        out.sort(key=lambda r: str(r.get("created_at") or ""), reverse=True)
        return out[: max(1, min(int(limit), 500))]
