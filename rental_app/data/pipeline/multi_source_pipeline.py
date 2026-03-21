# P7 Phase3：多平台统一调度 + 结果聚合（复用单平台 pipeline，不重写抓取逻辑）
from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from data.pipeline.rightmove_pipeline import run_rightmove_pipeline
from data.pipeline.zoopla_pipeline import run_zoopla_pipeline

_DEFAULT_SOURCES: tuple[str, ...] = ("rightmove", "zoopla")

# 仅聚合层消费、不传给子 pipeline 的 query 键
_MULTI_ONLY_QUERY_KEYS = frozenset(
    {"save_aggregated_sample", "save_analysis_sample"},
)

_DEBUG_DIR = Path(__file__).resolve().parent.parent / "scraper" / "samples" / "debug"
_AGG_SAMPLE_PATH = _DEBUG_DIR / "multi_source_aggregated_sample.json"

PipelineFn = Callable[..., Any]

PIPELINE_REGISTRY: dict[str, PipelineFn] = {
    "rightmove": run_rightmove_pipeline,
    "zoopla": run_zoopla_pipeline,
}


def _child_query(query: dict[str, Any] | None) -> dict[str, Any]:
    q = dict(query or {})
    for k in _MULTI_ONLY_QUERY_KEYS:
        q.pop(k, None)
    return q


def _identity_key(row: dict[str, Any]) -> tuple[str, str, str]:
    src = str(row.get("source") or "").strip().lower()
    lid = str(row.get("listing_id") or "").strip()
    if lid:
        return ("id", src, lid)
    url = str(row.get("source_url") or row.get("url") or "").strip()
    if url:
        return ("url", src, url)
    return (
        "weak",
        src,
        f"{row.get('title')!s}|{row.get('address')!s}",
    )


def dedupe_normalized_listings(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """基础去重：优先 (source+listing_id)，否则 (source+url)，避免单平台重复条被堆叠。"""
    seen: set[tuple[str, str, str]] = set()
    out: list[dict[str, Any]] = []
    for row in rows:
        key = _identity_key(row)
        if key in seen:
            continue
        seen.add(key)
        out.append(row)
    return out


def _strip_normalized_listings(r: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in r.items() if k != "normalized_listings"}


def _maybe_write_agg_sample(
    deduped: list[dict[str, Any]],
    *,
    enabled: bool,
) -> None:
    if not enabled or not deduped:
        return
    try:
        _AGG_SAMPLE_PATH.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "aggregated_unique_count": len(deduped),
            "sample": deduped[:5],
        }
        _AGG_SAMPLE_PATH.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except (OSError, TypeError, ValueError):
        pass


def run_source_pipeline(source: str, **kwargs: Any) -> Any:
    """
    单平台调度：未知 source 抛 `ValueError`（多平台入口会捕获并记入 errors）。
    """
    key = (source or "").strip().lower()
    fn = PIPELINE_REGISTRY.get(key)
    if fn is None:
        raise ValueError(f"unknown pipeline source: {source!r}")
    return fn(**kwargs)


def run_multi_source_pipeline(
    *,
    sources: list[str] | None = None,
    query: dict[str, Any] | None = None,
    limit_per_source: int = 20,
    persist: bool = True,
    storage_path: str | None = None,
    save_aggregated_sample: bool = False,
    include_aggregated_listings: bool = False,
) -> dict[str, Any]:
    """
    按顺序调用各平台 `run_*_pipeline`（带 `include_normalized_listings=True`），汇总统计并轻量去重聚合。

    - **success**：本次实际执行的每个 source 子结果均为 `success=True` 且无调度异常。
    - **跨平台**「同一物理房源」识别不在本阶段范围；仅做键级去重。
    """
    base_q = dict(query or {})
    save_agg = bool(save_aggregated_sample) or bool(
        base_q.get("save_aggregated_sample", False),
    )
    child_q = _child_query(base_q)

    want = sources if sources is not None else list(_DEFAULT_SOURCES)
    normalized_sources: list[str] = []
    errors: list[dict[str, Any]] = []
    per_source_raw: dict[str, dict[str, Any]] = {}

    for raw_src in want:
        src = (raw_src or "").strip().lower()
        if not src:
            continue
        if src not in PIPELINE_REGISTRY:
            errors.append(
                {"source": raw_src, "error": f"unknown source (skipped): {raw_src!r}"},
            )
            continue
        normalized_sources.append(src)
        try:
            r = PIPELINE_REGISTRY[src](
                query=child_q,
                limit=limit_per_source,
                persist=persist,
                storage_path=storage_path,
                include_normalized_listings=True,
            )
        except Exception as e:  # noqa: BLE001
            errors.append({"source": src, "error": f"{type(e).__name__}: {e}"})
            per_source_raw[src] = {
                "success": False,
                "error": str(e),
                "raw_count": 0,
                "normalized_count": 0,
                "normalization_skipped": 0,
                "saved": 0,
                "updated": 0,
                "skipped": 0,
            }
            continue
        per_source_raw[src] = dict(r)

    combined: list[dict[str, Any]] = []
    for src, r in per_source_raw.items():
        lst = r.get("normalized_listings")
        if isinstance(lst, list):
            for item in lst:
                if isinstance(item, dict):
                    combined.append(item)

    deduped = dedupe_normalized_listings(combined)
    _maybe_write_agg_sample(deduped, enabled=save_agg)

    per_source_stats = {
        k: _strip_normalized_listings(v) for k, v in per_source_raw.items()
    }

    total_raw = sum(int(v.get("raw_count") or 0) for v in per_source_stats.values())
    total_norm = sum(
        int(v.get("normalized_count") or 0) for v in per_source_stats.values()
    )
    total_norm_skip = sum(
        int(v.get("normalization_skipped") or 0) for v in per_source_stats.values()
    )
    total_saved = sum(int(v.get("saved") or 0) for v in per_source_stats.values())
    total_updated = sum(int(v.get("updated") or 0) for v in per_source_stats.values())
    total_skipped = sum(int(v.get("skipped") or 0) for v in per_source_stats.values())

    success = bool(normalized_sources) and all(
        per_source_stats[s].get("success") is True for s in normalized_sources
    )

    out: dict[str, Any] = {
        "success": success,
        "sources_requested": list(want),
        "sources_run": normalized_sources,
        "per_source_stats": per_source_stats,
        "errors": errors,
        "total_raw_count": total_raw,
        "total_normalized_count": total_norm,
        "total_normalization_skipped": total_norm_skip,
        "total_saved": total_saved,
        "total_updated": total_updated,
        "total_skipped": total_skipped,
        "aggregated_unique_count": len(deduped),
        "aggregated_listings_sample": deduped[:5],
    }
    if include_aggregated_listings:
        out["aggregated_listings"] = deduped
    return out


def run_multi_source_normalization_pipeline(**kwargs: Any) -> dict[str, Any]:
    """`run_multi_source_pipeline` 的别名。"""
    return run_multi_source_pipeline(**kwargs)
