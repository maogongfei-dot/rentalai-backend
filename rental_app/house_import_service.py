"""
Phase A4：房源 JSON/CSV 导入 → 解析 → clean_and_normalize → canonical（不落库）。
"""

from __future__ import annotations

import csv
import io
import json
import os
from pathlib import Path
from typing import Any

from house_source_adapters import clean_and_normalize_house_record

# 与推荐引擎一致的 canonical 结构；预览时省略 raw_source_data 以减小体积
_PREVIEW_STRIP_KEYS = frozenset({"raw_source_data"})

_IMPORT_MAX_BYTES = max(1, int(os.environ.get("RENTALAI_HOUSE_IMPORT_MAX_BYTES", str(5 * 1024 * 1024))))
_PREVIEW_LIMIT = max(1, int(os.environ.get("RENTALAI_HOUSE_IMPORT_PREVIEW", "3")))
_ERRORS_LIMIT = max(1, int(os.environ.get("RENTALAI_HOUSE_IMPORT_ERRORS_SHOWN", "10")))


def _decode_utf8_bytes(file_bytes: bytes) -> str:
    """编码容错：utf-8-sig 去 BOM，失败时 replace。"""
    if not file_bytes:
        return ""
    try:
        return file_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        return file_bytes.decode("utf-8", errors="replace")


def load_house_records_from_json_bytes(file_bytes: bytes) -> list[dict[str, Any]]:
    """
    JSON 解析：支持顶层 array，或 object 内 records / items / houses / listings。
    单 object 视为单条房源。
    """
    if not file_bytes or not file_bytes.strip():
        raise ValueError("empty file")

    text = _decode_utf8_bytes(file_bytes).strip()
    if not text:
        raise ValueError("empty file")

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError("invalid JSON: %s" % exc) from exc

    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]

    if isinstance(data, dict):
        for key in ("records", "items", "houses", "listings"):
            inner = data.get(key)
            if isinstance(inner, list):
                return [x for x in inner if isinstance(x, dict)]
        return [data]

    raise ValueError("JSON must be an array, an object with a records-like array, or one object")


def load_house_records_from_csv_bytes(file_bytes: bytes) -> list[dict[str, Any]]:
    """
    CSV 解析：首行为 header，DictReader 转 dict；空行跳过；字段名原样保留。
    """
    if not file_bytes or not file_bytes.strip():
        raise ValueError("empty file")

    text = _decode_utf8_bytes(file_bytes)
    # 统一换行，避免仅 \\r 的奇怪文件
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise ValueError("CSV has no header row")

    out: list[dict[str, Any]] = []
    for row in reader:
        if not isinstance(row, dict):
            continue
        # 跳过全空行
        if not any((v is not None and str(v).strip()) for v in row.values()):
            continue
        cleaned = {k: (v.strip() if isinstance(v, str) else v) for k, v in row.items() if k is not None}
        out.append(cleaned)

    return out


def _normalize_source_param(source: str | None) -> str:
    s = (source or "generic").strip().lower()
    return s if s else "generic"


def _strip_for_preview(rec: dict[str, Any]) -> dict[str, Any]:
    d = dict(rec)
    for k in _PREVIEW_STRIP_KEYS:
        d.pop(k, None)
    return d


def import_house_records(
    file_bytes: bytes,
    filename: str,
    source: str = "generic",
    *,
    return_full_records: bool = False,
) -> dict[str, Any]:
    """
    import service：按扩展名解析 → 逐条 clean_and_normalize → 统计成功/失败。
    return_full_records=True 时 result 含完整 canonical records（供 A5 推荐；体积可能较大）。
    返回 { ok, result } 或 { ok, error, message }。
    """
    fn = (filename or "").strip()
    ext = Path(fn).suffix.lower()

    if not file_bytes:
        return {
            "ok": False,
            "error": "empty_upload",
            "message": "uploaded file is empty",
        }

    if len(file_bytes) > _IMPORT_MAX_BYTES:
        return {
            "ok": False,
            "error": "file_too_large",
            "message": "file exceeds maximum size (%s bytes)" % _IMPORT_MAX_BYTES,
        }

    src = _normalize_source_param(source)

    try:
        if ext == ".json":
            raw_rows = load_house_records_from_json_bytes(file_bytes)
            file_type = "json"
        elif ext == ".csv":
            raw_rows = load_house_records_from_csv_bytes(file_bytes)
            file_type = "csv"
        else:
            return {
                "ok": False,
                "error": "unsupported_file_type",
                "message": "only .json and .csv are supported",
            }
    except ValueError as exc:
        return {
            "ok": False,
            "error": "parse_failed",
            "message": str(exc),
        }
    except Exception as exc:
        return {
            "ok": False,
            "error": "parse_failed",
            "message": str(exc),
        }

    if not raw_rows:
        return {
            "ok": False,
            "error": "no_records",
            "message": "no usable records found in file",
        }

    normalized: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    # 逐条导入统计：单条失败不拖垮整批；errors 仅保留前若干条便于排查
    for idx, row in enumerate(raw_rows):
        if not isinstance(row, dict):
            if len(errors) < _ERRORS_LIMIT:
                errors.append({"row_index": idx, "reason": "row is not an object"})
            continue
        try:
            canon = clean_and_normalize_house_record(row, source=src)
            normalized.append(canon)
        except Exception as exc:
            if len(errors) < _ERRORS_LIMIT:
                errors.append(
                    {
                        "row_index": idx,
                        "reason": (str(exc) or "normalize_failed")[:500],
                    }
                )

    failed_count = len(raw_rows) - len(normalized)

    preview = [_strip_for_preview(r) for r in normalized[:_PREVIEW_LIMIT]]

    result: dict[str, Any] = {
        "source": src,
        "file_type": file_type,
        "filename": fn or "upload",
        "imported_count": len(normalized),
        "failed_count": max(0, failed_count),
        "preview": preview,
        "errors": errors[:_ERRORS_LIMIT],
    }
    if return_full_records:
        result["records"] = normalized

    return {"ok": True, "result": result}


def recommend_from_imported_file(
    file_bytes: bytes,
    filename: str,
    raw_user_query: str,
    source: str = "generic",
) -> dict[str, Any]:
    """
    Phase A5：导入 → 全量 canonical → run_ai_analyze_with_records（不落库）。
    """
    imp = import_house_records(
        file_bytes, filename, source=source, return_full_records=True
    )
    if not imp.get("ok"):
        return imp
    from ai_recommendation_bridge import run_ai_analyze_with_records

    records = (imp.get("result") or {}).get("records") or []
    rec_out = run_ai_analyze_with_records(raw_user_query, records)
    return {
        "ok": True,
        "import": {k: v for k, v in (imp.get("result") or {}).items() if k != "records"},
        "recommendation": rec_out,
    }
