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

    def delete_record_for_user(self, record_id: str, user_id: str) -> str:
        """
        Remove one record by ``record_id`` only if ``userId`` on the row matches ``user_id``.

        Returns ``deleted`` | ``not_found`` | ``forbidden``.
        """
        rid = str(record_id or "").strip()
        uid = str(user_id or "").strip()
        if not rid or not uid:
            return "not_found"
        with _LOCK:
            doc = self.load_document()
            records = list(doc.get("records") or [])
            idx: int | None = None
            for i, r in enumerate(records):
                if not isinstance(r, dict):
                    continue
                if str(r.get("record_id") or "").strip() == rid:
                    idx = i
                    break
            if idx is None:
                return "not_found"
            row = records[idx]
            if str(row.get("userId") or "").strip() != uid:
                return "forbidden"
            records.pop(idx)
            doc["records"] = records
            self.save_document(doc)
        return "deleted"

    def delete_all_records_for_user(self, user_id: str) -> int:
        """
        Remove every record whose ``userId`` matches ``user_id``; leave all other rows unchanged.

        Returns the number of rows removed.
        """
        uid = str(user_id or "").strip()
        if not uid:
            return 0
        removed = 0
        with _LOCK:
            doc = self.load_document()
            records = list(doc.get("records") or [])
            kept: list[Any] = []
            for r in records:
                if not isinstance(r, dict):
                    kept.append(r)
                    continue
                if str(r.get("userId") or "").strip() == uid:
                    removed += 1
                else:
                    kept.append(dict(r))
            doc["records"] = kept
            self.save_document(doc)
        return removed
