"""
Phase A5：统一候选房源加载（canonical），供推荐引擎使用。
Phase D2：dataset=zoopla 时经 fetch_zoopla_listings(structured_query) → clean/normalize。
"""

from __future__ import annotations

from typing import Any

from house_samples_loader import load_house_samples, load_multi_source_house_samples
from house_source_adapters import clean_and_normalize_house_records

# Phase D2：最近一次 load_candidate_houses（zoopla）的轻量元数据，供 summary.source_mode 使用
_last_fetch_meta: dict[str, Any] = {}


def get_last_candidate_load_meta() -> dict[str, Any]:
    """返回最近一次 zoopla 加载的 ``zoopla_source_mode`` 等（无则空 dict）。"""
    return dict(_last_fetch_meta)


def load_candidate_houses(
    dataset: str = "realistic",
    structured_query: dict[str, Any] | None = None,
    imported_records: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """
    按数据来源返回已 clean + normalize 的 canonical 记录列表。
    - demo / realistic：从 JSON 加载后逐条 clean_and_normalize（行内 source 优先）
    - multi_source：与 loader 一致，已为 canonical
    - imported：使用调用方传入的原始行（如 A4 导入前格式）
    - zoopla：``fetch_zoopla_listings(structured_query)`` → clean_and_normalize（需传 structured_query）
    """
    global _last_fetch_meta

    _last_fetch_meta = {}

    ds = (dataset or "realistic").strip().lower()

    if ds == "imported":
        if not imported_records:
            return []
        return clean_and_normalize_house_records(imported_records, source=None)

    if ds == "multi_source":
        return load_multi_source_house_samples()

    if ds == "demo":
        raw = load_house_samples("demo")
        return clean_and_normalize_house_records(raw, source=None)

    if ds == "realistic":
        raw = load_house_samples("realistic")
        return clean_and_normalize_house_records(raw, source=None)

    # Phase D2：Zoopla HTTP 抓取 → canonical；失败时 scraper 内 mock，再空则 realistic
    if ds == "zoopla":
        from scraper.zoopla_scraper import fetch_zoopla_listings, fetch_zoopla_listings_with_meta

        sq = dict(structured_query or {})
        raw: list[dict[str, Any]] = []
        mode = "zoopla_mock_fallback"
        try:
            raw, mode = fetch_zoopla_listings_with_meta(sq)
        except Exception:
            # 全链路不崩：回退 scraper 自带 mock
            try:
                raw = fetch_zoopla_listings(sq)
                mode = "zoopla_mock_fallback"
            except Exception:
                raw = []
                mode = "zoopla_realistic_fallback"
        if not raw:
            raw = load_house_samples("realistic")
            mode = "zoopla_realistic_fallback"

        _last_fetch_meta = {"zoopla_source_mode": mode, "dataset": "zoopla"}
        out = clean_and_normalize_house_records(raw, source=None)
        if not out:
            _last_fetch_meta["zoopla_source_mode"] = "zoopla_realistic_fallback"
            out = clean_and_normalize_house_records(load_house_samples("realistic"), source=None)
        return out

    return []
