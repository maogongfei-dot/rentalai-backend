"""Minimal SQLite data layer for RentalAI records.

Stores three core record types:
1) task_records
2) analysis_records
3) property_records

This module is intentionally lightweight and stdlib-only (sqlite3).
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_DB_PATH = os.environ.get(
    "RENTALAI_RECORDS_DB_PATH",
    str(Path(__file__).resolve().parents[2] / ".rentalai_records.db"),
)
_DB_LOCK = threading.Lock()


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json_text(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    except (TypeError, ValueError):
        return "{}"


def _json_obj(text: str | None) -> Any:
    if not text:
        return None
    try:
        return json.loads(text)
    except (TypeError, ValueError):
        return None


def _connect() -> sqlite3.Connection:
    path = Path(_DB_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=5.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _build_task_result_summary(result: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(result, dict):
        return {}
    return {
        "success": bool(result.get("success")),
        "degraded": bool(result.get("degraded")),
        "pipeline_success": result.get("pipeline_success"),
        "sources_run": result.get("sources_run") or [],
        "aggregated_unique_count": result.get("aggregated_unique_count"),
        "total_analyzed_count": result.get("total_analyzed_count"),
        "error_count": len(result.get("errors") or []),
    }


def _input_hash(value: dict[str, Any] | None) -> str | None:
    if not isinstance(value, dict) or not value:
        return None
    payload = _json_text(value).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def normalize_analysis_input_signature(input_summary: dict[str, Any] | None) -> dict[str, Any]:
    """Build a stable, minimal input signature for cache matching."""
    src = input_summary if isinstance(input_summary, dict) else {}
    out: dict[str, Any] = {}
    sources = src.get("sources")
    if isinstance(sources, list):
        out["sources"] = sorted(
            {str(s).strip().lower() for s in sources if str(s).strip()}
        )
    elif isinstance(sources, str) and sources.strip():
        out["sources"] = [sources.strip().lower()]
    else:
        out["sources"] = []
    out["limit_per_source"] = int(src.get("limit_per_source") or 10)
    out["budget"] = src.get("budget")
    tp = src.get("target_postcode")
    out["target_postcode"] = str(tp).strip().upper() if isinstance(tp, str) and tp.strip() else None
    return out


def init_records_db() -> None:
    with _DB_LOCK:
        with _connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS task_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL UNIQUE,
                    task_type TEXT,
                    status TEXT,
                    input_summary TEXT,
                    result_summary TEXT,
                    error TEXT,
                    degraded INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT,
                    updated_at TEXT,
                    started_at TEXT,
                    finished_at TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS analysis_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    analysis_type TEXT NOT NULL,
                    input_hash TEXT,
                    input_summary TEXT,
                    result_summary TEXT,
                    raw_result_ref TEXT,
                    source TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_analysis_type_hash_created "
                "ON analysis_records (analysis_type, input_hash, created_at DESC)"
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS property_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source TEXT NOT NULL,
                    listing_url TEXT,
                    title TEXT,
                    postcode TEXT,
                    price REAL,
                    bedrooms REAL,
                    summary TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(source, listing_url)
                )
                """
            )
            conn.commit()


def upsert_task_record(task: dict[str, Any]) -> None:
    task_id = str(task.get("task_id") or "").strip()
    if not task_id:
        return
    task_type = str(task.get("task_type") or "multi_source_analysis")
    status = str(task.get("status") or "")
    input_summary = task.get("input_summary") if isinstance(task.get("input_summary"), dict) else {}
    result_obj = task.get("result") if isinstance(task.get("result"), dict) else {}
    result_summary = _build_task_result_summary(result_obj)
    with _DB_LOCK:
        with _connect() as conn:
            conn.execute(
                """
                INSERT INTO task_records (
                    task_id, task_type, status, input_summary, result_summary, error, degraded,
                    created_at, updated_at, started_at, finished_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(task_id) DO UPDATE SET
                    task_type=excluded.task_type,
                    status=excluded.status,
                    input_summary=excluded.input_summary,
                    result_summary=excluded.result_summary,
                    error=excluded.error,
                    degraded=excluded.degraded,
                    created_at=excluded.created_at,
                    updated_at=excluded.updated_at,
                    started_at=excluded.started_at,
                    finished_at=excluded.finished_at
                """,
                (
                    task_id,
                    task_type,
                    status,
                    _json_text(input_summary),
                    _json_text(result_summary),
                    task.get("error"),
                    1 if bool(task.get("degraded")) else 0,
                    task.get("created_at"),
                    task.get("updated_at"),
                    task.get("started_at"),
                    task.get("finished_at"),
                ),
            )
            conn.commit()


def insert_analysis_record(
    *,
    analysis_type: str,
    input_summary: dict[str, Any] | None,
    result_summary: dict[str, Any] | None,
    raw_result_ref: str | None = None,
    source: str = "unknown",
) -> int:
    now = _utc_now_iso()
    sig = normalize_analysis_input_signature(input_summary)
    with _DB_LOCK:
        with _connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO analysis_records (
                    analysis_type, input_hash, input_summary, result_summary, raw_result_ref, source, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    analysis_type,
                    _input_hash(sig),
                    _json_text(sig),
                    _json_text(result_summary or {}),
                    raw_result_ref,
                    source,
                    now,
                ),
            )
            conn.commit()
            return int(cur.lastrowid)


def find_reusable_analysis_result(
    *,
    analysis_type: str,
    input_summary: dict[str, Any] | None,
    max_age_seconds: int = 1800,
) -> dict[str, Any] | None:
    """Return cached full result when available and not expired.

    Cache payload is expected in analysis_records.result_summary:
      {
        "summary": {...},
        "reusable_result": {...}
      }
    """
    if not analysis_type:
        return None
    sig = normalize_analysis_input_signature(input_summary)
    h = _input_hash(sig)
    if not h:
        return None
    now = datetime.now(timezone.utc)
    with _DB_LOCK:
        with _connect() as conn:
            row = conn.execute(
                """
                SELECT result_summary, created_at
                FROM analysis_records
                WHERE analysis_type = ? AND input_hash = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (analysis_type, h),
            ).fetchone()
    if not row:
        return None
    created_raw = row["created_at"]
    try:
        created_dt = datetime.fromisoformat(created_raw)
        age = (now - created_dt).total_seconds()
        if age > max(1, int(max_age_seconds)):
            return None
    except (TypeError, ValueError):
        return None
    payload = _json_obj(row["result_summary"])
    if not isinstance(payload, dict):
        return None
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    if summary.get("success") is not True:
        return None
    if bool(summary.get("degraded")):
        return None
    if summary.get("cacheable") is False:
        return None
    reusable = payload.get("reusable_result")
    if not isinstance(reusable, dict):
        return None
    return reusable


def upsert_property_records(rows: list[dict[str, Any]]) -> dict[str, int]:
    inserted = 0
    updated = 0
    skipped = 0
    now = _utc_now_iso()
    with _DB_LOCK:
        with _connect() as conn:
            for row in rows:
                if not isinstance(row, dict):
                    skipped += 1
                    continue
                source = str(row.get("source") or "unknown").strip().lower() or "unknown"
                listing_url = row.get("source_url") or row.get("listing_url")
                title = row.get("title")
                postcode = row.get("postcode")
                price = row.get("rent_pcm") if row.get("rent_pcm") is not None else row.get("rent")
                bedrooms = row.get("bedrooms")
                summary = row.get("summary")

                if listing_url is None or str(listing_url).strip() == "":
                    conn.execute(
                        """
                        INSERT INTO property_records (
                            source, listing_url, title, postcode, price, bedrooms, summary, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (source, None, title, postcode, price, bedrooms, summary, now, now),
                    )
                    inserted += 1
                    continue

                listing_url = str(listing_url).strip()
                existing = conn.execute(
                    "SELECT id FROM property_records WHERE source = ? AND listing_url = ?",
                    (source, listing_url),
                ).fetchone()
                if existing:
                    conn.execute(
                        """
                        UPDATE property_records
                        SET title = ?, postcode = ?, price = ?, bedrooms = ?, summary = ?, updated_at = ?
                        WHERE source = ? AND listing_url = ?
                        """,
                        (title, postcode, price, bedrooms, summary, now, source, listing_url),
                    )
                    updated += 1
                else:
                    conn.execute(
                        """
                        INSERT INTO property_records (
                            source, listing_url, title, postcode, price, bedrooms, summary, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (source, listing_url, title, postcode, price, bedrooms, summary, now, now),
                    )
                    inserted += 1
            conn.commit()
    return {"inserted": inserted, "updated": updated, "skipped": skipped}


def list_task_records(limit: int = 50) -> list[dict[str, Any]]:
    limit = min(max(int(limit), 1), 200)
    with _DB_LOCK:
        with _connect() as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM task_records
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
    out: list[dict[str, Any]] = []
    for row in rows:
        d = dict(row)
        d["degraded"] = bool(d.get("degraded"))
        d["input_summary"] = _json_obj(d.get("input_summary"))
        d["result_summary"] = _json_obj(d.get("result_summary"))
        out.append(d)
    return out


def list_analysis_records(limit: int = 50) -> list[dict[str, Any]]:
    limit = min(max(int(limit), 1), 200)
    with _DB_LOCK:
        with _connect() as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM analysis_records
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
    out: list[dict[str, Any]] = []
    for row in rows:
        d = dict(row)
        d["input_summary"] = _json_obj(d.get("input_summary"))
        d["result_summary"] = _json_obj(d.get("result_summary"))
        out.append(d)
    return out


def list_property_records(limit: int = 50) -> list[dict[str, Any]]:
    limit = min(max(int(limit), 1), 200)
    with _DB_LOCK:
        with _connect() as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM property_records
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
    return [dict(r) for r in rows]

