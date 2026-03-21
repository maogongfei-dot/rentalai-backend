# P6 Phase4：Rightmove 抓取 → normalizer → storage 闭环（单页、无 Zoopla）
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TypedDict

from data.normalizer.listing_normalizer import normalize_listing_batch
from data.schema.listing_schema import ListingSchema, is_valid_listing_payload
from data.scraper.rightmove_scraper import RightmoveScraper
from data.storage import save_listings

# 仅 pipeline 消费、不传给 RightmoveScraper 的 query 键
_PIPELINE_QUERY_KEYS = frozenset({"save_normalized_sample"})

_DEBUG_DIR = Path(__file__).resolve().parent.parent / "scraper" / "samples" / "debug"
_RAW_SAMPLE_PATH = _DEBUG_DIR / "rightmove_raw_sample.json"
_NORMALIZED_SAMPLE_PATH = _DEBUG_DIR / "rightmove_normalized_sample.json"


class RightmovePipelineResult(TypedDict, total=False):
    success: bool
    error: str | None
    raw_count: int
    normalized_count: int
    normalization_skipped: int
    saved: int
    updated: int
    skipped: int
    sample_normalized: dict[str, Any] | None
    normalized_listings: list[dict[str, Any]]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _scrape_query(query: dict[str, Any] | None) -> dict[str, Any]:
    q = dict(query or {})
    for k in _PIPELINE_QUERY_KEYS:
        q.pop(k, None)
    return q


def _maybe_write_sample(path: Path, payload: Any) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except (OSError, TypeError, ValueError):
        pass


def _maybe_attach_normalized_listings(
    out: RightmovePipelineResult,
    normalized: list[ListingSchema] | None,
    include: bool,
) -> RightmovePipelineResult:
    """供多平台聚合层拉取标准化结果；默认不附加以减小返回体积。"""
    if not include:
        return out
    o: dict[str, Any] = dict(out)
    if normalized is None:
        o["normalized_listings"] = []
    else:
        o["normalized_listings"] = [L.to_dict() for L in normalized]
    return o  # type: ignore[return-value]


def run_rightmove_pipeline(
    *,
    query: dict[str, Any] | None = None,
    limit: int = 20,
    persist: bool = True,
    storage_path: str | None = None,
    save_raw_sample: bool = False,
    save_normalized_sample: bool = False,
    include_normalized_listings: bool = False,
) -> RightmovePipelineResult:
    """
    RightmoveScraper → normalize_listing_batch(source=rightmove) → save_listings。

    - `normalization_skipped`：`is_valid_listing_payload` 未通过的核心弱记录数。
    - `skipped`：storage 批量保存时单条失败计数（与 `save_listings` 语义一致）。
    - `include_normalized_listings=True` 时附加 `normalized_listings`（供多平台聚合）。
    """
    base_q = dict(query or {})
    save_raw_flag = bool(save_raw_sample) or bool(base_q.get("save_raw_sample", False))
    save_norm_flag = bool(save_normalized_sample) or bool(
        base_q.get("save_normalized_sample", False),
    )

    scrape_q = _scrape_query(base_q)
    if save_raw_flag:
        scrape_q.pop("save_raw_sample", None)
    err: str | None = None
    raw_rows: list[dict[str, Any]] = []
    try:
        raw_rows = RightmoveScraper().scrape(query=scrape_q, limit=limit)
    except Exception as e:  # noqa: BLE001 — 闭环需结构化返回
        err = f"{type(e).__name__}: {e}"
        return _maybe_attach_normalized_listings(
            {
                "success": False,
                "error": err,
                "raw_count": 0,
                "normalized_count": 0,
                "normalization_skipped": 0,
                "saved": 0,
                "updated": 0,
                "skipped": 0,
                "sample_normalized": None,
            },
            None,
            include_normalized_listings,
        )

    stamp = _utc_now_iso()
    stamped: list[dict[str, Any]] = []
    for row in raw_rows:
        r = dict(row)
        r.setdefault("scraped_at", stamp)
        stamped.append(r)

    if save_raw_flag and stamped:
        _maybe_write_sample(
            _RAW_SAMPLE_PATH,
            {"count": len(stamped), "sample": stamped[:3]},
        )

    normalized: list[ListingSchema] = []
    try:
        normalized = normalize_listing_batch(stamped, source="rightmove")
    except Exception as e:
        err = f"{type(e).__name__}: {e}"
        return _maybe_attach_normalized_listings(
            {
                "success": False,
                "error": err,
                "raw_count": len(stamped),
                "normalized_count": 0,
                "normalization_skipped": 0,
                "saved": 0,
                "updated": 0,
                "skipped": 0,
                "sample_normalized": None,
            },
            [],
            include_normalized_listings,
        )

    norm_skip = sum(
        1
        for L in normalized
        if not is_valid_listing_payload(L.to_dict())
    )

    if save_norm_flag and normalized:
        _maybe_write_sample(
            _NORMALIZED_SAMPLE_PATH,
            {
                "count": len(normalized),
                "sample": [L.to_dict() for L in normalized[:3]],
            },
        )

    if persist:
        sr = save_listings(normalized, file_path=storage_path)
        storage_ok = bool(sr.get("success"))
        out: RightmovePipelineResult = {
            "success": storage_ok and err is None,
            "error": err,
            "raw_count": len(stamped),
            "normalized_count": len(normalized),
            "normalization_skipped": norm_skip,
            "saved": int(sr.get("saved", 0)),
            "updated": int(sr.get("updated", 0)),
            "skipped": int(sr.get("skipped", 0)),
            "sample_normalized": normalized[0].to_dict() if normalized else None,
        }
        if not storage_ok and err is None:
            out["error"] = "storage write failed"
        return _maybe_attach_normalized_listings(
            out, normalized, include_normalized_listings
        )

    return _maybe_attach_normalized_listings(
        {
            "success": True,
            "error": err,
            "raw_count": len(stamped),
            "normalized_count": len(normalized),
            "normalization_skipped": norm_skip,
            "saved": 0,
            "updated": 0,
            "skipped": 0,
            "sample_normalized": normalized[0].to_dict() if normalized else None,
        },
        normalized,
        include_normalized_listings,
    )


def scrape_and_normalize_rightmove(
    **kwargs: Any,
) -> RightmovePipelineResult:
    """`run_rightmove_pipeline` 的别名。"""
    return run_rightmove_pipeline(**kwargs)


def run_rightmove_normalization_pipeline(
    **kwargs: Any,
) -> RightmovePipelineResult:
    """`run_rightmove_pipeline` 的别名。"""
    return run_rightmove_pipeline(**kwargs)
