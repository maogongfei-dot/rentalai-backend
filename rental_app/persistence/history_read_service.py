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
    uid = str(row.get("userId") or row.get("user_id") or "")
    res = row.get("result")
    if res is None:
        res = row.get("result_snapshot")
    return {
        "record_id": str(row.get("record_id") or ""),
        "userId": uid,
        "user_id": uid,
        "type": str(row.get("type") or ""),
        "title": str(row.get("title") or ""),
        "created_at": str(row.get("created_at") or ""),
        "input": row.get("input") if row.get("input") is not None else "",
        "summary": row.get("summary") if isinstance(row.get("summary"), dict) else {},
        "result": res,
        "result_snapshot": row.get("result_snapshot") if row.get("result_snapshot") is not None else res,
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


def delete_public_record_for_user(record_id: str, user_id: str) -> str:
    """
    Delete a server-side history row if it belongs to ``user_id``.

    Returns ``deleted`` | ``not_found`` | ``forbidden`` (same semantics as
    :meth:`HistoryRepository.delete_record_for_user`).
    """
    return _REPO.delete_record_for_user(record_id, user_id)


def clear_public_records_for_user(user_id: str) -> int:
    """Remove all server-side history rows for ``user_id``. Returns number removed."""
    return _REPO.delete_all_records_for_user(user_id)
