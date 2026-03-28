"""
Phase A5：统一候选房源加载（canonical），供推荐引擎使用。
Phase D2：dataset=zoopla 时经 fetch_zoopla_listings(structured_query) → clean/normalize。
Phase D4：Zoopla 抓取结果先经 scraped_listing_cleaner（去重/清洗）再 normalize。
Phase D5：dataset=rightmove 经 fetch_rightmove_listings → 同一套 cleaner + normalize。
"""

from __future__ import annotations

import logging
from typing import Any

from house_samples_loader import load_house_samples, load_multi_source_house_samples
from house_source_adapters import clean_and_normalize_house_records

logger = logging.getLogger(__name__)

# Phase D2/D5：最近一次 load_candidate_houses（zoopla / rightmove / market_combined）的元数据，供 summary 使用
_last_fetch_meta: dict[str, Any] = {}


def get_last_candidate_load_meta() -> dict[str, Any]:
    """返回最近一次加载的 ``zoopla_source_mode`` / ``rightmove_source_mode`` / ``scrape_clean_stats`` 等。"""
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
    - zoopla：``fetch_zoopla_listings`` → ``prepare_scraped_listings_for_recommendation``（D4 清洗去重）→ canonical
    - rightmove：``fetch_rightmove_listings`` → 同上（source=rightmove）
    - market_combined：zoopla + rightmove 合并后再 cleaner（预留 D5）
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

    # Phase D2+D4：Zoopla 抓取 → D4 清洗去重 → normalize_house_records；失败时 mock / realistic
    if ds == "zoopla":
        from data.scraped_listing_cleaner import (
            get_last_scrape_clean_stats,
            prepare_scraped_listings_for_recommendation,
        )
        from scraper.zoopla_scraper import fetch_zoopla_listings, fetch_zoopla_listings_with_meta

        sq = dict(structured_query or {})
        raw: list[dict[str, Any]] = []
        mode = "zoopla_mock_fallback"
        try:
            raw, mode = fetch_zoopla_listings_with_meta(sq)
        except Exception:
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
        out = prepare_scraped_listings_for_recommendation(raw, source="zoopla")
        _last_fetch_meta["scrape_clean_stats"] = get_last_scrape_clean_stats()
        if not out:
            _last_fetch_meta["zoopla_source_mode"] = "zoopla_realistic_fallback"
            out = prepare_scraped_listings_for_recommendation(load_house_samples("realistic"), source="zoopla")
            _last_fetch_meta["scrape_clean_stats"] = get_last_scrape_clean_stats()
        return out

    # Phase D5：Rightmove —— 与 Zoopla 共享 cleaner → normalize → recommendation
    if ds == "rightmove":
        from data.scraped_listing_cleaner import (
            get_last_scrape_clean_stats,
            prepare_scraped_listings_for_recommendation,
        )
        from scraper.rightmove_scraper import fetch_rightmove_listings, fetch_rightmove_listings_with_meta

        sq = dict(structured_query or {})
        raw: list[dict[str, Any]] = []
        mode = "rightmove_mock_fallback"
        try:
            raw, mode = fetch_rightmove_listings_with_meta(sq)
        except Exception:
            try:
                raw = fetch_rightmove_listings(sq)
                mode = "rightmove_mock_fallback"
            except Exception:
                raw = []
                mode = "rightmove_realistic_fallback"
        if not raw:
            raw = load_house_samples("realistic")
            mode = "rightmove_realistic_fallback"

        _last_fetch_meta = {"rightmove_source_mode": mode, "dataset": "rightmove"}
        out = prepare_scraped_listings_for_recommendation(raw, source="rightmove")
        _last_fetch_meta["scrape_clean_stats"] = get_last_scrape_clean_stats()
        logger.info(
            "rightmove loader: mode=%s raw_count=%s canonical_count=%s",
            mode,
            len(raw),
            len(out),
        )
        if not out:
            _last_fetch_meta["rightmove_source_mode"] = "rightmove_realistic_fallback"
            out = prepare_scraped_listings_for_recommendation(load_house_samples("realistic"), source="rightmove")
            _last_fetch_meta["scrape_clean_stats"] = get_last_scrape_clean_stats()
        return out

    # 预留：双源合并（zoopla + rightmove）→ 统一 cleaner 去重 → 逐条 source 进 normalize
    if ds == "market_combined":
        from data.scraped_listing_cleaner import (
            get_last_scrape_clean_stats,
            prepare_scraped_listings_for_recommendation,
        )
        from scraper.rightmove_scraper import fetch_rightmove_listings_with_meta
        from scraper.zoopla_scraper import fetch_zoopla_listings_with_meta

        sq = dict(structured_query or {})
        raw_z: list[dict[str, Any]] = []
        raw_r: list[dict[str, Any]] = []
        mz = "zoopla_mock_fallback"
        mr = "rightmove_mock_fallback"
        try:
            raw_z, mz = fetch_zoopla_listings_with_meta(sq)
        except Exception:
            raw_z = []
        try:
            raw_r, mr = fetch_rightmove_listings_with_meta(sq)
        except Exception:
            raw_r = []
        merged: list[dict[str, Any]] = []
        for r in raw_z:
            x = dict(r)
            x.setdefault("source", "zoopla")
            merged.append(x)
        for r in raw_r:
            x = dict(r)
            x.setdefault("source", "rightmove")
            merged.append(x)
        _last_fetch_meta = {
            "dataset": "market_combined",
            "zoopla_source_mode": mz,
            "rightmove_source_mode": mr,
        }
        # source=None：仅对缺 source 的行不强行写默认；合并行已带 zoopla/rightmove
        out = prepare_scraped_listings_for_recommendation(merged, source=None)
        _last_fetch_meta["scrape_clean_stats"] = get_last_scrape_clean_stats()
        if not out:
            out = prepare_scraped_listings_for_recommendation(load_house_samples("realistic"), source=None)
            _last_fetch_meta["scrape_clean_stats"] = get_last_scrape_clean_stats()
        return out

    return []
