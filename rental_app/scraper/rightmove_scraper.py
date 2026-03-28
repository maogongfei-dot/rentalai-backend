# Rightmove 租赁列表：Phase D5 推荐链路统一入口（requests/BS4 骨架 + 可选 Playwright + mock fallback）
# 与 zoopla_scraper 并列：fetch_* → scraped_listing_cleaner → normalize → recommendation
from __future__ import annotations

import logging
import os
import re
from typing import Any
from urllib.parse import urlencode, urljoin

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# 默认关闭 Playwright 第二道（避免冷启动阻塞；设为 1 时 requests 空则尝试 data 层浏览器抓取）
_RIGHTMOVE_USE_PLAYWRIGHT = os.environ.get("RENTALAI_RIGHTMOVE_USE_PLAYWRIGHT", "0").strip().lower() in (
    "1",
    "true",
    "yes",
)

_RIGHTMOVE_ORIGIN = "https://www.rightmove.co.uk"

_DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-GB,en;q=0.9",
    "Cache-Control": "no-cache",
}

_UK_POSTCODE_RE = re.compile(
    r"\b([A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2})\b",
    re.I,
)
_PROPERTY_HREF_RE = re.compile(r"/properties/(\d+)", re.I)
_PRICE_PCM_RE = re.compile(
    r"£\s*([\d,]+(?:\.\d+)?)\s*(?:pcm|p\.c\.m\.|per\s*month|/month)?",
    re.I,
)
_PRICE_ANY_RE = re.compile(r"£\s*([\d,]+(?:\.\d+)?)")


def listing_id_from_property_href(href: str | None) -> str | None:
    if not href:
        return None
    m = _PROPERTY_HREF_RE.search(href)
    return m.group(1) if m else None


# 与 data.scraper.rightmove_scraper 默认伦敦 URL 对齐，便于调试
DEFAULT_RIGHTMOVE_SEARCH_URL = (
    "https://www.rightmove.co.uk/property-to-rent/find.html?"
    "searchLocation=London&useLocationIdentifier=true&locationIdentifier=REGION%5E87490&radius=0.0"
)

# 城市 → 列表页 URL 预设（不完整抓取时仍可用 search_url 覆盖）
_CITY_SEARCH_URLS: dict[str, str] = {
    "london": DEFAULT_RIGHTMOVE_SEARCH_URL,
    "milton keynes": (
        "https://www.rightmove.co.uk/property-to-rent/find.html?"
        "searchLocation=Milton+Keynes&useLocationIdentifier=true&locationIdentifier=REGION%5E59898&radius=0.0"
    ),
    "manchester": (
        "https://www.rightmove.co.uk/property-to-rent/find.html?"
        "searchLocation=Manchester&useLocationIdentifier=true&locationIdentifier=REGION%5E90487&radius=0.0"
    ),
}


def _slug_city(city: str) -> str:
    return re.sub(r"\s+", " ", city.strip().lower())


def _build_search_url(query: dict[str, Any]) -> str:
    """由 city / postcode / budget_max 构造列表页 URL（与 structured_query 兼容）。"""
    q = dict(query or {})
    override = (q.get("search_url") or q.get("url") or "").strip()
    if override:
        return override

    city = (q.get("city") or "").strip()
    postcode = (q.get("postcode") or "").strip()
    base = f"{_RIGHTMOVE_ORIGIN}/property-to-rent/find.html"
    price_q: dict[str, str] = {}
    if q.get("budget_max") is not None:
        try:
            mx = int(float(q["budget_max"]))
            if mx > 0:
                price_q["maxPrice"] = str(mx)
        except (TypeError, ValueError):
            pass

    if city:
        key = _slug_city(city)
        if key in _CITY_SEARCH_URLS:
            url = _CITY_SEARCH_URLS[key]
            if price_q:
                sep = "&" if "?" in url else "?"
                return f"{url}{sep}{urlencode(price_q)}"
            return url
        params = {
            "searchLocation": city,
            "useLocationIdentifier": "true",
            **price_q,
        }
        return f"{base}?{urlencode(params)}"

    if postcode:
        params = {
            "searchLocation": postcode,
            "useLocationIdentifier": "true",
            **price_q,
        }
        return f"{base}?{urlencode(params)}"

    url = DEFAULT_RIGHTMOVE_SEARCH_URL
    if price_q:
        return f"{url}&{urlencode(price_q)}"
    return url


def _parse_pcm(price_text: str) -> float | None:
    if not price_text:
        return None
    m = _PRICE_PCM_RE.search(price_text) or _PRICE_ANY_RE.search(price_text)
    if not m:
        return None
    try:
        return float(m.group(1).replace(",", ""))
    except ValueError:
        return None


def _extract_postcode(address: str, fallback: str) -> str:
    m = _UK_POSTCODE_RE.search(address or "")
    if m:
        return m.group(1).upper().replace("  ", " ").strip()
    return (fallback or "").strip().upper()


def _guess_area_from_address(address: str, city: str) -> str:
    if not address:
        return city or ""
    parts = [p.strip() for p in address.split(",") if p.strip()]
    if len(parts) >= 2:
        return parts[-2]
    return city or ""


def _normalize_row(
    *,
    listing_id: str,
    title: str,
    address: str,
    price_text: str,
    bedrooms_text: str | None,
    property_type: str | None,
    summary: str | None,
    source_url: str,
    query: dict[str, Any],
) -> dict[str, Any] | None:
    rent_pcm = _parse_pcm(price_text) or _parse_pcm(address)
    if rent_pcm is None or rent_pcm <= 0:
        return None
    city_q = (query.get("city") or "").strip() or "London"
    pc_q = (query.get("postcode") or "").strip()
    postcode = _extract_postcode(address, pc_q)
    city = city_q
    area_name = _guess_area_from_address(address, city)
    beds = bedrooms_text or ""
    return {
        "listing_id": listing_id,
        "title": (title or address or "Rightmove listing")[:500],
        "address": address.strip() if address else "",
        "postcode": postcode,
        "area_name": area_name or city,
        "city": city,
        "rent_pcm": float(rent_pcm),
        "bedrooms": beds,
        "property_type": (property_type or "Property").strip() or "Property",
        "source": "rightmove",
        "source_url": source_url,
        "summary": summary or "",
    }


def _parse_listing_card_bs4(card: Any, page_url: str, query: dict[str, Any]) -> dict[str, Any] | None:
    link = card.select_one('a[href*="/properties/"]')
    if link is None:
        return None
    href = link.get("href") or ""
    lid = listing_id_from_property_href(href)
    if not lid:
        return None
    source_url = urljoin(page_url, href)

    price_el = card.select_one('[class*="PropertyPrice_price__"]')
    price_text = price_el.get_text(" ", strip=True) if price_el else ""
    addr_el = card.select_one('[class*="PropertyAddress_address__"]')
    address = addr_el.get_text(" ", strip=True) if addr_el else ""

    tb = card.select_one('[class*="PropertyCardTitle_container"]')
    title_block = tb.get_text("\n", strip=True) if tb else ""
    title_line = (title_block.splitlines()[0].strip() if title_block else "") or address

    sum_el = card.select_one('[class*="PropertyCardSummary_summary"]')
    summary = sum_el.get_text(" ", strip=True) if sum_el else ""

    pt_el = card.select_one('[class*="PropertyInformation_propertyType"]')
    prop_type = pt_el.get_text(" ", strip=True) if pt_el else ""

    bed_el = card.select_one('[class*="PropertyInformation_bedroomsCount"]')
    beds = bed_el.get_text(" ", strip=True) if bed_el else ""

    if not price_text:
        blob = card.get_text(" ", strip=True)
        price_text = blob

    row = _normalize_row(
        listing_id=lid,
        title=title_line,
        address=address,
        price_text=price_text,
        bedrooms_text=beds or None,
        property_type=prop_type or None,
        summary=summary or None,
        source_url=source_url,
        query=query,
    )
    return row


def _parse_html_listings(html: str, page_url: str, query: dict[str, Any]) -> list[dict[str, Any]]:
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select("[data-testid^='propertyCard-']")
    if not cards:
        cards = []
        for tag in soup.find_all(attrs={"data-testid": True}):
            tid = tag.get("data-testid") or ""
            if isinstance(tid, str) and tid.startswith("propertyCard-"):
                cards.append(tag)
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for card in cards:
        row = _parse_listing_card_bs4(card, page_url, query)
        if not row:
            continue
        lid = str(row.get("listing_id") or "")
        if lid in seen:
            continue
        seen.add(lid)
        out.append(row)
    return out


def _fetch_live_requests(query: dict[str, Any]) -> list[dict[str, Any]]:
    url = _build_search_url(query)
    r = requests.get(url, headers=_DEFAULT_HEADERS, timeout=25)
    r.raise_for_status()
    final_url = r.url or url
    listings = _parse_html_listings(r.text, final_url, query)
    return listings


def _fetch_live_playwright(query: dict[str, Any], limit: int = 25) -> list[dict[str, Any]]:
    """第二道：沿用 data 层 Playwright 解析（与 listing_scraper 一致）。"""
    try:
        from data.scraper.rightmove_scraper import RightmoveScraper

        rows = RightmoveScraper().scrape(query=dict(query or {}), limit=limit)
    except Exception as exc:
        logger.warning("rightmove playwright scrape failed: %s", exc)
        return []
    out: list[dict[str, Any]] = []
    for raw in rows:
        if not isinstance(raw, dict):
            continue
        href = raw.get("source_url") or raw.get("url") or ""
        lid = raw.get("listing_id") or listing_id_from_property_href(str(href))
        if not lid:
            continue
        price_t = str(raw.get("price") or "")
        addr = str(raw.get("address") or "")
        title = str(raw.get("title") or addr or "Listing")
        row = _normalize_row(
            listing_id=str(lid),
            title=title,
            address=addr,
            price_text=price_t,
            bedrooms_text=str(raw.get("bedrooms") or "") or None,
            property_type=str(raw.get("property_type") or "") or None,
            summary=str(raw.get("summary") or "") or None,
            source_url=str(href),
            query=query,
        )
        if row is None:
            continue
        out.append(row)
    return out


def _mock_listings(query: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Rightmove 风格 mock：≥5 条，覆盖 Milton Keynes / London / Manchester。
    真实抓取失败时保证 dataset=rightmove 仍可跑推荐。
    """
    q = dict(query or {})
    try:
        budget = int(float(q.get("budget_max"))) if q.get("budget_max") is not None else 2000
    except (TypeError, ValueError):
        budget = 2000

    templates: list[dict[str, Any]] = [
        {
            "listing_id": "rm-mk-100001",
            "title": "1 bedroom apartment to rent in Central Milton Keynes",
            "address": "Midsummer Boulevard, Milton Keynes",
            "postcode": "MK9 2UB",
            "area_name": "Central Milton Keynes",
            "city": "Milton Keynes",
            "rent_pcm": min(950.0, float(budget)),
            "bedrooms": 1.0,
            "property_type": "Apartment",
            "summary": "Modern flat, close to shops and station.",
        },
        {
            "listing_id": "rm-lon-100002",
            "title": "Studio flat in Zone 2 — bills included",
            "address": "Bethnal Green Road, London",
            "postcode": "E2 6AB",
            "area_name": "Bethnal Green",
            "city": "London",
            "rent_pcm": min(1200.0, float(budget)),
            "bedrooms": 0.0,
            "property_type": "Studio",
            "summary": "Bills included; 8 min walk to tube.",
            "bills_included": True,
        },
        {
            "listing_id": "rm-mcr-100003",
            "title": "2 bed terraced house to rent — near tram",
            "address": "Wilmslow Road, Manchester",
            "postcode": "M14 6NL",
            "area_name": "Fallowfield",
            "city": "Manchester",
            "rent_pcm": min(850.0, float(budget)),
            "bedrooms": 2.0,
            "property_type": "Terraced",
            "summary": "Two double bedrooms; convenient for university and city centre.",
        },
        {
            "listing_id": "rm-mk-100004",
            "title": "2 bedroom maisonette — Milton Keynes",
            "address": "Bletchley, Milton Keynes",
            "postcode": "MK3 5DU",
            "area_name": "Bletchley",
            "city": "Milton Keynes",
            "rent_pcm": min(1100.0, float(budget)),
            "bedrooms": 2.0,
            "property_type": "Maisonette",
            "summary": "Parking space; quiet residential area.",
        },
        {
            "listing_id": "rm-lon-100005",
            "title": "1 bed flat to rent in Clapham",
            "address": "North Street, London",
            "postcode": "SW4 0HD",
            "area_name": "Clapham",
            "city": "London",
            "rent_pcm": min(1150.0, float(budget)),
            "bedrooms": 1.0,
            "property_type": "Flat",
            "summary": "Bright reception; near Clapham Common.",
        },
        {
            "listing_id": "rm-mcr-100006",
            "title": "1 bedroom apartment — Manchester city centre",
            "address": "Whitworth Street West, Manchester",
            "postcode": "M1 5BE",
            "area_name": "City Centre",
            "city": "Manchester",
            "rent_pcm": min(775.0, float(budget)),
            "bedrooms": 1.0,
            "property_type": "Apartment",
            "summary": "Concierge; short walk to Piccadilly station.",
        },
    ]

    base = _RIGHTMOVE_ORIGIN
    out: list[dict[str, Any]] = []
    for t in templates:
        row = {
            **t,
            "source": "rightmove",
            "source_url": f"{base}/properties/{t['listing_id']}",
        }
        out.append(row)
    return out


def fetch_rightmove_listings_with_meta(query: dict) -> tuple[list[dict], str]:
    """
    返回 ``(records, source_mode)``。

    - ``live_rightmove``：requests+BS4 或 Playwright 解析到至少一条
    - ``rightmove_mock_fallback``：内置 mock（与 zoopla 一样优先打通链路）
    """
    q = dict(query or {})
    logger.info("rightmove fetch: building url from structured_query keys=%s", list(q.keys()))

    rows: list[dict[str, Any]] = []
    mode = "rightmove_mock_fallback"

    # 1) requests + BeautifulSoup
    try:
        rows = _fetch_live_requests(q)
        if rows:
            mode = "live_rightmove"
            logger.info(
                "rightmove: live requests+BS4 ok raw_count=%s (cleaner count logged in loader)",
                len(rows),
            )
            return rows, mode
    except Exception as exc:
        logger.warning("rightmove: requests fetch failed (%s), try playwright", exc)

    # 2) Playwright（可选，与 data.scraper.rightmove 共用）
    rows = []
    if _RIGHTMOVE_USE_PLAYWRIGHT:
        rows = _fetch_live_playwright(q, limit=25)
    if rows:
        mode = "live_rightmove"
        logger.info("rightmove: live playwright ok raw_count=%s", len(rows))
        return rows, mode

    # 3) fallback mock —— 保证推荐链路有候选
    logger.info("rightmove: using mock fallback (live scrape empty or failed)")
    rows = _mock_listings(q)
    return rows, "rightmove_mock_fallback"


def fetch_rightmove_listings(query: dict) -> list[dict]:
    """对外统一入口（推荐 loader 使用）。"""
    rows, _ = fetch_rightmove_listings_with_meta(query)
    return rows


__all__ = [
    "DEFAULT_RIGHTMOVE_SEARCH_URL",
    "fetch_rightmove_listings",
    "fetch_rightmove_listings_with_meta",
    "listing_id_from_property_href",
]
