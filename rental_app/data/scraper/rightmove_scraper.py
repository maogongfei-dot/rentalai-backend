# P3 Phase4 + P6 Phase3：Rightmove 列表页真实抓取（原始 dict，不接 normalizer/storage）
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from data.scraper.playwright_runner import (
    _optional_debug_artifacts,
    browser_page_for_scraper_config,
    playwright_available,
)
from data.scraper.scraper_config import ScraperRunConfig
from data.scraper.selectors.rightmove_selectors import (
    ADDRESS,
    BEDROOMS_COUNT,
    CARD_ROOT,
    LINK_PROPERTY,
    PRICE_PRIMARY,
    PROPERTY_TYPE,
    SUMMARY,
    TITLE_BLOCK,
)

from .base_scraper import BaseListingScraper

# 默认可用伦敦区域列表 URL 做本地调试（可通过 query["search_url"] 覆盖）
DEFAULT_RIGHTMOVE_SEARCH_URL = (
    "https://www.rightmove.co.uk/property-to-rent/find.html?"
    "searchLocation=London&useLocationIdentifier=true&locationIdentifier=REGION%5E87490&radius=0.0"
)

_QUERY_CONFIG_KEYS = frozenset(
    {
        "search_url",
        "url",
        "headless",
        "debug",
        "save_raw_sample",
        "save_raw_html",
        "save_screenshots",
        "output_dir",
    }
)

_DEBUG_SAMPLE_PATH = (
    Path(__file__).resolve().parent / "samples" / "debug" / "rightmove_raw_sample.json"
)


def listing_id_from_property_href(href: str | None) -> str | None:
    if not href:
        return None
    m = re.search(r"/properties/(\d+)", href)
    return m.group(1) if m else None


def _safe_text(locator: Any) -> str:
    try:
        return (locator.first.inner_text(timeout=5_000) or "").strip()
    except Exception:
        return ""


def _safe_attr(locator: Any, name: str) -> str | None:
    try:
        return locator.first.get_attribute(name)
    except Exception:
        return None


def _parse_listing_card(card: Any, page_url: str) -> dict[str, Any] | None:
    href = _safe_attr(card.locator(LINK_PROPERTY), "href")
    if not href:
        return None
    lid = listing_id_from_property_href(href)
    if not lid:
        return None
    abs_url = _absolute_url(href, page_url)
    price = _safe_text(card.locator(PRICE_PRIMARY))
    address = _safe_text(card.locator(ADDRESS))
    title_block = _safe_text(card.locator(TITLE_BLOCK))
    title_line = (title_block.splitlines()[0].strip() if title_block else "") or address
    summary = _safe_text(card.locator(SUMMARY))
    prop_type = _safe_text(card.locator(PROPERTY_TYPE))
    beds = _safe_text(card.locator(BEDROOMS_COUNT))
    return {
        "source": "rightmove",
        "listing_id": lid,
        "title": title_line or None,
        "price": price or None,
        "bedrooms": beds or None,
        "address": address or None,
        "url": abs_url,
        # 与 normalizer 主字段 `source_url` 对齐（`_base_alias_map` 亦识别 `url`）
        "source_url": abs_url,
        "property_type": prop_type or None,
        "summary": summary or None,
    }


def _absolute_url(href: str, page_url: str) -> str:
    from urllib.parse import urljoin

    return urljoin(page_url, href)


def _extract_listing_cards(page: Any, base_url: str, limit: int) -> tuple[int, list[dict[str, Any]]]:
    roots = page.locator(CARD_ROOT)
    try:
        roots.first.wait_for(state="visible", timeout=45_000)
    except Exception:
        pass
    n = roots.count()
    cap = max(limit, 0)
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for i in range(n):
        if len(out) >= cap:
            break
        card = roots.nth(i)
        try:
            row = _parse_listing_card(card, base_url)
        except Exception:
            continue
        if not row:
            continue
        lid = row.get("listing_id")
        if isinstance(lid, str) and lid in seen:
            continue
        if isinstance(lid, str):
            seen.add(lid)
        out.append(row)
    return n, out


def _fetch_rightmove_page(config: ScraperRunConfig) -> tuple[int, list[dict[str, Any]]]:
    """单次浏览器会话：可选调试落盘 + 解析。失败返回 (0, [])。"""
    if not (config.search_url or "").strip():
        return 0, []
    if not playwright_available():
        return 0, []
    cap = max(config.limit, 0)
    try:
        with browser_page_for_scraper_config(config) as page:
            try:
                page.wait_for_selector(CARD_ROOT, timeout=45_000)
            except Exception:
                pass
            if config.save_raw_html or config.save_screenshots:
                try:
                    _optional_debug_artifacts(page, page.content(), config)
                except Exception:
                    pass
            base = page.url
            return _extract_listing_cards(page, base, cap)
    except Exception:
        return 0, []


def _scraper_run_config_from_query(
    query: dict[str, Any] | None,
    limit: int,
) -> tuple[ScraperRunConfig, dict[str, Any]]:
    q = dict(query or {})
    url = q.get("search_url")
    if url is None:
        url = q.get("url")
    if url is None:
        url = DEFAULT_RIGHTMOVE_SEARCH_URL
    url = (url or "").strip()
    rest = {k: v for k, v in q.items() if k not in _QUERY_CONFIG_KEYS}
    cfg = ScraperRunConfig(
        source="rightmove",
        search_url=url,
        query=rest,
        max_pages=1,
        limit=limit,
        headless=bool(q.get("headless", True)),
        save_raw_html=bool(q.get("save_raw_html", False)),
        save_screenshots=bool(q.get("save_screenshots", False)),
        output_dir=q.get("output_dir"),
    )
    flags = {
        "debug": bool(q.get("debug", False)),
        "save_raw_sample": bool(q.get("save_raw_sample", False)),
    }
    return cfg, flags


def rightmove_raw_from_config(config: ScraperRunConfig) -> list[dict[str, Any]]:
    """
    使用已构造的 `ScraperRunConfig` 抓取一页列表（不翻页），返回原始 dict 列表。
    供 `run_playwright_scrape` 与内部 `scrape` 复用。
    """
    _, rows = _fetch_rightmove_page(config)
    return rows


def _maybe_save_raw_sample(rows: list[dict[str, Any]]) -> None:
    try:
        _DEBUG_SAMPLE_PATH.parent.mkdir(parents=True, exist_ok=True)
        payload = {"count": len(rows), "sample": rows[:3]}
        _DEBUG_SAMPLE_PATH.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except OSError:
        pass


class RightmoveScraper(BaseListingScraper):
    """Rightmove 租赁列表页：单页、`limit` 条上限；输出原始字段 dict。"""

    source = "rightmove"

    def __init__(self) -> None:
        self.last_scrape_stats: dict[str, int] | None = None

    def scrape(
        self,
        query: dict[str, Any] | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        cfg, flags = _scraper_run_config_from_query(query, limit)
        if not cfg.search_url:
            self.last_scrape_stats = {"cards_in_dom": 0, "parsed_ok": 0}
            return []

        n_dom, listings = _fetch_rightmove_page(cfg)
        self.last_scrape_stats = {
            "cards_in_dom": n_dom,
            "parsed_ok": len(listings),
        }

        if flags["debug"]:
            print(
                f"[rightmove] cards_in_dom={n_dom} parsed_ok={len(listings)} limit={limit}",
            )
            if listings:
                sample = {
                    k: listings[0].get(k)
                    for k in ("listing_id", "title", "price", "url")
                }
                print(f"[rightmove] sample: {sample}")

        if flags["save_raw_sample"] and listings:
            _maybe_save_raw_sample(listings)

        return listings
