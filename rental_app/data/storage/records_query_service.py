"""Minimal query service for history/records endpoints.

Keeps response shaping out of route handlers.
"""

from __future__ import annotations

from typing import Any

from data.storage.records_db import (
    get_task_record_by_task_id_for_user,
    list_analysis_records,
    list_property_records,
    list_task_records,
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
                "source": r.get("source"),
                "created_at": r.get("created_at"),
            }
        )
    return out


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

