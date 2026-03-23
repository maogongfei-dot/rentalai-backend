"""Minimal SQLite data layer for RentalAI records.

Stores core record types:
1) task_records
2) analysis_records
3) property_records
4) favorite_records (P10 Phase2)

This module is intentionally lightweight and stdlib-only (sqlite3).
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import threading
import uuid
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
    lu = src.get("listing_url")
    out["listing_url"] = str(lu).strip() if isinstance(lu, str) and lu.strip() else None
    hid = src.get("history_task_id")
    out["history_task_id"] = (
        str(hid).strip() if isinstance(hid, str) and str(hid).strip() else None
    )
    # P10 Phase7 — optional UX preferences (cache signature only; does not change scoring formulas)
    pt = src.get("property_type")
    out["property_type"] = str(pt).strip().lower() if isinstance(pt, str) and pt.strip() else None
    br = src.get("bedrooms")
    if isinstance(br, (int, float)) and br == int(br):
        out["bedrooms"] = str(int(br))
    elif isinstance(br, str) and br.strip():
        out["bedrooms"] = br.strip().upper()
    else:
        out["bedrooms"] = None
    bt = src.get("bathrooms")
    if isinstance(bt, (int, float)):
        out["bathrooms"] = float(bt)
    elif isinstance(bt, str) and bt.strip():
        try:
            out["bathrooms"] = float(bt.strip())
        except ValueError:
            out["bathrooms"] = None
    else:
        out["bathrooms"] = None
    dc = src.get("distance_to_centre")
    out["distance_to_centre"] = (
        str(dc).strip().lower() if isinstance(dc, str) and str(dc).strip() else None
    )
    sp = src.get("safety_preference")
    out["safety_preference"] = (
        str(sp).strip().lower() if isinstance(sp, str) and str(sp).strip() else None
    )
    return out


def init_records_db() -> None:
    with _DB_LOCK:
        with _connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS task_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL UNIQUE,
                    user_id TEXT,
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
                    user_id TEXT,
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
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    email TEXT NOT NULL UNIQUE,
                    password TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            _ensure_column(conn, "task_records", "user_id", "TEXT")
            _ensure_column(conn, "analysis_records", "user_id", "TEXT")
            _ensure_column(conn, "analysis_records", "explain_summary", "TEXT")
            _ensure_column(conn, "analysis_records", "pros", "TEXT")
            _ensure_column(conn, "analysis_records", "cons", "TEXT")
            _ensure_column(conn, "analysis_records", "risk_flags", "TEXT")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS favorite_records (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    listing_url TEXT,
                    property_id TEXT,
                    title TEXT,
                    price REAL,
                    postcode TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_favorites_user_created "
                "ON favorite_records (user_id, created_at DESC)"
            )
            conn.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_favorites_user_url "
                "ON favorite_records (user_id, listing_url) "
                "WHERE listing_url IS NOT NULL AND listing_url != ''"
            )
            conn.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_favorites_user_prop "
                "ON favorite_records (user_id, property_id) "
                "WHERE property_id IS NOT NULL AND property_id != ''"
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
                    task_id, user_id, task_type, status, input_summary, result_summary, error, degraded,
                    created_at, updated_at, started_at, finished_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(task_id) DO UPDATE SET
                    user_id=excluded.user_id,
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
                    task.get("user_id"),
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
    user_id: str | None = None,
    explain_summary: str | None = None,
    pros: list[Any] | None = None,
    cons: list[Any] | None = None,
    risk_flags: list[Any] | None = None,
) -> int:
    now = _utc_now_iso()
    sig = normalize_analysis_input_signature(input_summary)
    with _DB_LOCK:
        with _connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO analysis_records (
                    user_id, analysis_type, input_hash, input_summary, result_summary,
                    raw_result_ref, source, created_at,
                    explain_summary, pros, cons, risk_flags
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    analysis_type,
                    _input_hash(sig),
                    _json_text(sig),
                    _json_text(result_summary or {}),
                    raw_result_ref,
                    source,
                    now,
                    explain_summary,
                    _json_text(pros if pros is not None else []),
                    _json_text(cons if cons is not None else []),
                    _json_text(risk_flags if risk_flags is not None else []),
                ),
            )
            conn.commit()
            return int(cur.lastrowid)


def find_reusable_analysis_result(
    *,
    analysis_type: str,
    input_summary: dict[str, Any] | None,
    user_id: str | None = None,
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
                (
                    """
                    SELECT result_summary, created_at
                    FROM analysis_records
                    WHERE analysis_type = ? AND input_hash = ? AND user_id = ?
                    ORDER BY id DESC
                    LIMIT 1
                    """
                    if user_id is not None
                    else """
                    SELECT result_summary, created_at
                    FROM analysis_records
                    WHERE analysis_type = ? AND input_hash = ? AND user_id IS NULL
                    ORDER BY id DESC
                    LIMIT 1
                    """
                ),
                ((analysis_type, h, user_id) if user_id is not None else (analysis_type, h)),
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


def list_task_records(limit: int = 50, *, user_id: str | None = None) -> list[dict[str, Any]]:
    limit = min(max(int(limit), 1), 200)
    with _DB_LOCK:
        with _connect() as conn:
            rows = conn.execute(
                (
                    """
                    SELECT *
                    FROM task_records
                    WHERE user_id = ?
                    ORDER BY updated_at DESC
                    LIMIT ?
                    """
                    if user_id is not None
                    else """
                    SELECT *
                    FROM task_records
                    ORDER BY updated_at DESC
                    LIMIT ?
                    """
                ),
                ((user_id, limit) if user_id is not None else (limit,)),
            ).fetchall()
    out: list[dict[str, Any]] = []
    for row in rows:
        out.append(_task_row_to_dict(row))
    return out


def get_task_record_by_task_id(task_id: str) -> dict[str, Any] | None:
    tid = str(task_id or "").strip()
    if not tid:
        return None
    with _DB_LOCK:
        with _connect() as conn:
            row = conn.execute(
                """
                SELECT *
                FROM task_records
                WHERE task_id = ?
                LIMIT 1
                """,
                (tid,),
            ).fetchone()
    if row is None:
        return None
    return _task_row_to_dict(row)


def get_task_record_by_task_id_for_user(task_id: str, *, user_id: str) -> dict[str, Any] | None:
    tid = str(task_id or "").strip()
    uid = str(user_id or "").strip()
    if not tid or not uid:
        return None
    with _DB_LOCK:
        with _connect() as conn:
            row = conn.execute(
                """
                SELECT *
                FROM task_records
                WHERE task_id = ? AND user_id = ?
                LIMIT 1
                """,
                (tid, uid),
            ).fetchone()
    if row is None:
        return None
    return _task_row_to_dict(row)


UI_HISTORY_ANALYSIS_TYPE = "p10_ui_history"


def list_ui_history_records(limit: int = 50, *, user_id: str) -> list[dict[str, Any]]:
    """Phase3 UI 保存的分析快照（按用户、最新优先）。"""
    uid = str(user_id or "").strip()
    if not uid:
        return []
    limit = min(max(int(limit), 1), 200)
    with _DB_LOCK:
        with _connect() as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM analysis_records
                WHERE user_id = ? AND analysis_type = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (uid, UI_HISTORY_ANALYSIS_TYPE, limit),
            ).fetchall()
    return [_analysis_row_to_dict(r) for r in rows]


def get_ui_history_record_for_user(record_id: int, *, user_id: str) -> dict[str, Any] | None:
    uid = str(user_id or "").strip()
    if not uid or record_id <= 0:
        return None
    with _DB_LOCK:
        with _connect() as conn:
            row = conn.execute(
                """
                SELECT *
                FROM analysis_records
                WHERE id = ? AND user_id = ? AND analysis_type = ?
                LIMIT 1
                """,
                (int(record_id), uid, UI_HISTORY_ANALYSIS_TYPE),
            ).fetchone()
    if row is None:
        return None
    return _analysis_row_to_dict(row)


def list_analysis_records(limit: int = 50, *, user_id: str | None = None) -> list[dict[str, Any]]:
    limit = min(max(int(limit), 1), 200)
    with _DB_LOCK:
        with _connect() as conn:
            rows = conn.execute(
                (
                    """
                    SELECT *
                    FROM analysis_records
                    WHERE user_id = ?
                    ORDER BY id DESC
                    LIMIT ?
                    """
                    if user_id is not None
                    else """
                    SELECT *
                    FROM analysis_records
                    ORDER BY id DESC
                    LIMIT ?
                    """
                ),
                ((user_id, limit) if user_id is not None else (limit,)),
            ).fetchall()
    out: list[dict[str, Any]] = []
    for row in rows:
        out.append(_analysis_row_to_dict(row))
    return out


def _analysis_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    d = dict(row)
    d["input_summary"] = _json_obj(d.get("input_summary"))
    d["result_summary"] = _json_obj(d.get("result_summary"))
    d["pros"] = _json_obj(d.get("pros"))
    d["cons"] = _json_obj(d.get("cons"))
    d["risk_flags"] = _json_obj(d.get("risk_flags"))
    if not isinstance(d.get("pros"), list):
        d["pros"] = []
    if not isinstance(d.get("cons"), list):
        d["cons"] = []
    if not isinstance(d.get("risk_flags"), list):
        d["risk_flags"] = []
    return d


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


def _task_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    d = dict(row)
    d["degraded"] = bool(d.get("degraded"))
    d["input_summary"] = _json_obj(d.get("input_summary"))
    d["result_summary"] = _json_obj(d.get("result_summary"))
    return d


def create_user(email: str, password: str) -> dict[str, Any] | None:
    em = str(email or "").strip().lower()
    pw = str(password or "")
    if not em or not pw:
        return None
    user_id = uuid.uuid4().hex
    now = _utc_now_iso()
    with _DB_LOCK:
        with _connect() as conn:
            try:
                conn.execute(
                    """
                    INSERT INTO users (id, email, password, created_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (user_id, em, _password_hash(pw), now),
                )
                conn.commit()
            except sqlite3.IntegrityError:
                return None
    return {"id": user_id, "email": em, "created_at": now}


def email_exists(email: str) -> bool:
    em = str(email or "").strip().lower()
    if not em:
        return False
    with _DB_LOCK:
        with _connect() as conn:
            row = conn.execute(
                "SELECT 1 AS ok FROM users WHERE email = ? LIMIT 1",
                (em,),
            ).fetchone()
    return row is not None


def get_user_by_id(user_id: str) -> dict[str, Any] | None:
    """Return id, email, created_at (no password)."""
    uid = str(user_id or "").strip()
    if not uid:
        return None
    with _DB_LOCK:
        with _connect() as conn:
            row = conn.execute(
                """
                SELECT id, email, created_at
                FROM users
                WHERE id = ?
                LIMIT 1
                """,
                (uid,),
            ).fetchone()
    if row is None:
        return None
    return {"id": row["id"], "email": row["email"], "created_at": row["created_at"]}


def verify_user(email: str, password: str) -> dict[str, Any] | None:
    em = str(email or "").strip().lower()
    pw = str(password or "")
    if not em or not pw:
        return None
    with _DB_LOCK:
        with _connect() as conn:
            row = conn.execute(
                """
                SELECT id, email, created_at, password
                FROM users
                WHERE email = ?
                LIMIT 1
                """,
                (em,),
            ).fetchone()
    if row is None:
        return None
    if row["password"] != _password_hash(pw):
        return None
    return {"id": row["id"], "email": row["email"], "created_at": row["created_at"]}


def _password_hash(password: str) -> str:
    return hashlib.sha256(str(password).encode("utf-8")).hexdigest()


def insert_favorite_record(
    user_id: str,
    *,
    listing_url: str | None = None,
    property_id: str | None = None,
    title: str | None = None,
    price: float | None = None,
    postcode: str | None = None,
) -> dict[str, Any] | None:
    """Insert a favorite; returns None on duplicate (minimal dedupe)."""
    uid = str(user_id or "").strip()
    if not uid:
        return None
    url = (str(listing_url).strip() if listing_url else "") or None
    pid = str(property_id).strip() if property_id else ""
    pid = pid or None
    if not url and not pid:
        return None
    fav_id = uuid.uuid4().hex
    now = _utc_now_iso()
    tit = (title or "").strip() or None
    pc = (postcode or "").strip() or None
    with _DB_LOCK:
        with _connect() as conn:
            try:
                conn.execute(
                    """
                    INSERT INTO favorite_records (
                        id, user_id, listing_url, property_id, title, price, postcode, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (fav_id, uid, url, pid, tit, price, pc, now),
                )
                conn.commit()
            except sqlite3.IntegrityError:
                return None
    return {
        "id": fav_id,
        "user_id": uid,
        "listing_url": url,
        "property_id": pid,
        "title": tit,
        "price": price,
        "postcode": pc,
        "created_at": now,
    }


def delete_favorite_record(user_id: str, favorite_id: str) -> bool:
    uid = str(user_id or "").strip()
    fid = str(favorite_id or "").strip()
    if not uid or not fid:
        return False
    with _DB_LOCK:
        with _connect() as conn:
            cur = conn.execute(
                "DELETE FROM favorite_records WHERE id = ? AND user_id = ?",
                (fid, uid),
            )
            conn.commit()
            return cur.rowcount > 0


def list_favorite_records(user_id: str, limit: int = 100) -> list[dict[str, Any]]:
    uid = str(user_id or "").strip()
    if not uid:
        return []
    limit = min(max(int(limit), 1), 500)
    with _DB_LOCK:
        with _connect() as conn:
            rows = conn.execute(
                """
                SELECT id, user_id, listing_url, property_id, title, price, postcode, created_at
                FROM favorite_records
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (uid, limit),
            ).fetchall()
    return [dict(r) for r in rows]


def _ensure_column(conn: sqlite3.Connection, table: str, column: str, col_type: str) -> None:
    rows = conn.execute("PRAGMA table_info(%s)" % table).fetchall()
    names = {r[1] for r in rows}
    if column in names:
        return
    conn.execute("ALTER TABLE %s ADD COLUMN %s %s" % (table, column, col_type))

