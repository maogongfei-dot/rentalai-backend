"""Minimal query service for history/records endpoints.

Keeps response shaping out of route handlers.
"""

from __future__ import annotations

from typing import Any

from data.storage.records_db import (
    get_task_record_by_task_id_for_user,
    get_ui_history_record_for_user,
    list_analysis_records,
    list_property_records,
    list_task_records,
    list_ui_history_records,
)


def get_recent_task_records(limit: int = 30, *, user_id: str) -> list[dict[str, Any]]:
    rows = list_task_records(limit=limit, user_id=user_id)
    out: list[dict[str, Any]] = []
    for r in rows:
        out.append(
            {
                "task_id": r.get("task_id"),
                "task_type": r.get("task_type"),
                "status": r.get("status"),
                "input_summary": r.get("input_summary"),
                "result_summary": r.get("result_summary"),
                "error": r.get("error"),
                "created_at": r.get("created_at"),
                "updated_at": r.get("updated_at"),
            }
        )
    return out


def get_task_record_detail(task_id: str, *, user_id: str) -> dict[str, Any] | None:
    r = get_task_record_by_task_id_for_user(task_id, user_id=user_id)
    if r is None:
        return None
    return {
        "task_id": r.get("task_id"),
        "task_type": r.get("task_type"),
        "status": r.get("status"),
        "input_summary": r.get("input_summary"),
        "result_summary": r.get("result_summary"),
        "error": r.get("error"),
        "degraded": r.get("degraded"),
        "created_at": r.get("created_at"),
        "updated_at": r.get("updated_at"),
        "started_at": r.get("started_at"),
        "finished_at": r.get("finished_at"),
    }


def get_recent_analysis_records(limit: int = 30, *, user_id: str) -> list[dict[str, Any]]:
    rows = list_analysis_records(limit=limit, user_id=user_id)
    out: list[dict[str, Any]] = []
    for r in rows:
        out.append(
            {
                "analysis_type": r.get("analysis_type"),
                "input_hash": r.get("input_hash"),
                "input_summary": r.get("input_summary"),
                "result_summary": r.get("result_summary"),
                "explain_summary": r.get("explain_summary"),
                "pros": r.get("pros") or [],
                "cons": r.get("cons") or [],
                "risk_flags": r.get("risk_flags") or [],
                "source": r.get("source"),
                "created_at": r.get("created_at"),
            }
        )
    return out


def ui_history_item_view(row: dict[str, Any]) -> dict[str, Any]:
    """history 列表行：供 Phase3 `/records/ui-history` 使用。"""
    rs = row.get("result_summary") if isinstance(row.get("result_summary"), dict) else {}
    dp = rs.get("display_payload") if isinstance(rs.get("display_payload"), dict) else {}
    header = dp.get("header") if isinstance(dp.get("header"), dict) else {}
    prop = dp.get("property") if isinstance(dp.get("property"), dict) else {}
    ex = dp.get("explain") if isinstance(dp.get("explain"), dict) else {}
    return {
        "record_id": row.get("id"),
        "created_at": row.get("created_at"),
        "task_id": rs.get("task_id"),
        "input_value": rs.get("input_value") if rs.get("input_value") is not None else "",
        "title": prop.get("title"),
        "final_score": header.get("final_score"),
        "verdict": header.get("verdict_label"),
        "summary_line": row.get("explain_summary") or ex.get("summary"),
    }


def get_ui_history_items(limit: int = 50, *, user_id: str) -> list[dict[str, Any]]:
    rows = list_ui_history_records(limit=limit, user_id=user_id)
    return [ui_history_item_view(r) for r in rows]


def get_ui_history_detail(record_id: int, *, user_id: str) -> dict[str, Any] | None:
    row = get_ui_history_record_for_user(record_id, user_id=user_id)
    if row is None:
        return None
    rs = row.get("result_summary") if isinstance(row.get("result_summary"), dict) else {}
    return {
        "record_id": row.get("id"),
        "created_at": row.get("created_at"),
        "user_id": row.get("user_id"),
        "saved_result_payload": rs,
        "explain_summary": row.get("explain_summary"),
        "pros": row.get("pros") or [],
        "cons": row.get("cons") or [],
        "risk_flags": row.get("risk_flags") or [],
    }


def get_recent_property_records(limit: int = 30) -> list[dict[str, Any]]:
    rows = list_property_records(limit=limit)
    out: list[dict[str, Any]] = []
    for r in rows:
        out.append(
            {
                "source": r.get("source"),
                "listing_url": r.get("listing_url"),
                "title": r.get("title"),
                "postcode": r.get("postcode"),
                "price": r.get("price"),
                "bedrooms": r.get("bedrooms"),
                "updated_at": r.get("updated_at"),
            }
        )
    return out

