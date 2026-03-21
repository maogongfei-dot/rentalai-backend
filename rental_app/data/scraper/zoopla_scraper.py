# P3 Phase4 + P7 Phase1：Zoopla 租赁列表页真实抓取（原始 dict，不接 normalizer/storage）
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
from data.scraper.selectors.zoopla_selectors import (
    ADDRESS,
    CARD_ROOT,
    CARD_ROOT_FALLBACK,
    CARD_WAIT,
    PRICE_PRIMARY,
    SUMMARY,
)

from .base_scraper import BaseListingScraper

# 默认伦敦租赁列表（可通过 query["search_url"] / url 覆盖）
DEFAULT_ZOOPLA_SEARCH_URL = "https://www.zoopla.co.uk/to-rent/property/london/"

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
    Path(__file__).resolve().parent / "samples" / "debug" / "zoopla_raw_sample.json"
)

_PROPERTY_TYPE_RE = re.compile(
    r"\b(studio|flat|apartment|maisonette|penthouse|"
    r"detached|semi-detached|terraced|bungalow|house|cottage)\b",
    re.I,
)


def listing_id_from_zoopla_href(href: str | None) -> str | None:
    if not href:
        return None
    m = re.search(r"/to-rent/details/(\d+)", href, re.I)
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


def _detail_href_from_card(card: Any) -> str | None:
    try:
        return card.evaluate(
            """
            el => {
              let p = el;
              for (let i = 0; i < 8 && p; i++, p = p.parentElement) {
                const a = p.querySelector('a[href*="/to-rent/details/"]');
                if (a) return a.getAttribute('href');
              }
              return null;
            }
            """,
        )
    except Exception:
        return None


def _bedrooms_from_card(card: Any) -> str:
    try:
        t = card.inner_text(timeout=5_000)
    except Exception:
        return ""
    m = re.search(r"(\d+)\s*beds?\b", t, re.I)
    return m.group(1) if m else ""


def _property_type_hint(summary: str, card_plain: str) -> str | None:
    for blob in (summary, card_plain):
        if not blob:
            continue
        m = _PROPERTY_TYPE_RE.search(blob)
        if m:
            return m.group(1)
    return None


def _absolute_url(href: str, page_url: str) -> str:
    from urllib.parse import urljoin

    return urljoin(page_url, href)


def _card_roots(page: Any) -> Any:
    loc = page.locator(CARD_ROOT)
    try:
        if loc.count() > 0:
            return loc
    except Exception:
        pass
    return page.locator(CARD_ROOT_FALLBACK)


def _parse_listing_card(card: Any, page_url: str) -> dict[str, Any] | None:
    href = _detail_href_from_card(card)
    if not href:
        return None
    lid = listing_id_from_zoopla_href(href)
    if not lid:
        return None
    abs_url = _absolute_url(href, page_url)
    price = _safe_text(card.locator(PRICE_PRIMARY))
    address = _safe_text(card.locator(ADDRESS))
    if not address:
        address = _safe_text(card.locator("address"))
    summary = _safe_text(card.locator(SUMMARY))
    beds = _bedrooms_from_card(card)
    try:
        card_plain = card.inner_text(timeout=3_000)
    except Exception:
        card_plain = ""
    ptype = _property_type_hint(summary, card_plain)
    title_line = (address or (summary.splitlines()[0].strip() if summary else "")) or None
    return {
        "source": "zoopla",
        "listing_id": lid,
        "title": title_line,
        "price": price or None,
        "bedrooms": beds or None,
        "address": address or None,
        "url": abs_url,
        "source_url": abs_url,
        "property_type": ptype,
        "summary": summary or None,
    }


def _extract_listing_cards(page: Any, base_url: str, limit: int) -> tuple[int, list[dict[str, Any]]]:
    roots = _card_roots(page)
    try:
        roots.first.wait_for(state="visible", timeout=45_000)
    except Exception:
        pass
    try:
        page.wait_for_timeout(1_500)
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


def _fetch_zoopla_page(config: ScraperRunConfig) -> tuple[int, list[dict[str, Any]]]:
    if not (config.search_url or "").strip():
        return 0, []
    if not playwright_available():
        return 0, []
    cap = max(config.limit, 0)
    try:
        with browser_page_for_scraper_config(config) as page:
            try:
                page.wait_for_selector(CARD_WAIT, timeout=45_000)
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
        url = DEFAULT_ZOOPLA_SEARCH_URL
    url = (url or "").strip()
    rest = {k: v for k, v in q.items() if k not in _QUERY_CONFIG_KEYS}
    cfg = ScraperRunConfig(
        source="zoopla",
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


def zoopla_raw_from_config(config: ScraperRunConfig) -> list[dict[str, Any]]:
    """单页列表抓取；供 `run_playwright_scrape` 与 `ZooplaScraper.scrape` 复用。"""
    _, rows = _fetch_zoopla_page(config)
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


class ZooplaScraper(BaseListingScraper):
    """Zoopla 租赁列表页：单页、`limit` 条；输出与 Rightmove 对齐的 raw dict。"""

    source = "zoopla"

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

        n_dom, listings = _fetch_zoopla_page(cfg)
        self.last_scrape_stats = {
            "cards_in_dom": n_dom,
            "parsed_ok": len(listings),
        }

        if flags["debug"]:
            print(
                f"[zoopla] cards_in_dom={n_dom} parsed_ok={len(listings)} limit={limit}",
            )
            if listings:
                sample = {
                    k: listings[0].get(k)
                    for k in ("listing_id", "title", "price", "url")
                }
                print(f"[zoopla] sample: {sample}")

        if flags["save_raw_sample"] and listings:
            _maybe_save_raw_sample(listings)

        return listings
