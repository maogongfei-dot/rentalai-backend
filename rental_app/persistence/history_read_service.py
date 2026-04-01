"""
Phase 5 Round3 Step4 — Read path for server-side JSON history (public-safe record shape).
"""

from __future__ import annotations

from typing import Any

from .history_repository import HistoryRepository

_REPO = HistoryRepository()


def serialize_record_for_api(row: dict[str, Any]) -> dict[str, Any]:
    """Stable fields for HTTP responses (no internal-only keys)."""
    if not isinstance(row, dict):
        return {}
    return {
        "record_id": str(row.get("record_id") or ""),
        "userId": str(row.get("userId") or ""),
        "type": str(row.get("type") or ""),
        "title": str(row.get("title") or ""),
        "created_at": str(row.get("created_at") or ""),
        "summary": row.get("summary") if isinstance(row.get("summary"), dict) else {},
        "result_snapshot": row.get("result_snapshot"),
    }


def list_public_records(
    user_id: str,
    *,
    record_type: str | None = None,
    limit: int = 200,
) -> list[dict[str, Any]]:
    rows = _REPO.list_by_user(
        user_id,
        limit=limit,
        record_type=record_type,
    )
    return [serialize_record_for_api(r) for r in rows]
