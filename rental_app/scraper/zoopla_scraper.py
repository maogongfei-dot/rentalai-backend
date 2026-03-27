# Zoopla 租赁列表：requests + BeautifulSoup；失败时返回固定 mock 数据
from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlencode, urljoin

import requests
from bs4 import BeautifulSoup

_ZOOPLA_ORIGIN = "https://www.zoopla.co.uk"

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
_DETAIL_ID_RE = re.compile(r"/to-rent/details/(\d+)", re.I)
_BEDS_RE = re.compile(r"(\d+)\s*beds?\b", re.I)
_PROPERTY_TYPE_RE = re.compile(
    r"\b(studio|flat|apartment|maisonette|penthouse|"
    r"detached|semi-detached|terraced|bungalow|house|cottage)\b",
    re.I,
)
_PRICE_PCM_RE = re.compile(
    r"£\s*([\d,]+(?:\.\d+)?)\s*(?:pcm|p\.c\.m\.|per\s*month|/month)?",
    re.I,
)
_PRICE_ANY_RE = re.compile(r"£\s*([\d,]+(?:\.\d+)?)")


def _slugify_location(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", name.strip().lower())
    return s.strip("-") or "london"


def _postcode_outcode(pc: str) -> str:
    t = pc.strip().upper().replace("  ", " ")
    if not t:
        return ""
    # UK: outward code is before the last segment (inward)
    parts = t.split()
    return parts[0] if parts else ""


def _price_params(budget_max: Any) -> dict[str, str]:
    if budget_max is None:
        return {}
    try:
        mx = int(float(budget_max))
        if mx <= 0:
            return {}
        return {"price_frequency": "per_month", "price_max": str(mx)}
    except (TypeError, ValueError):
        return {}


def _build_search_url(query: dict[str, Any]) -> str:
    """Build Zoopla to-rent search URL from city / postcode / budget_max."""
    q = dict(query or {})
    override = (q.get("search_url") or q.get("url") or "").strip()
    if override:
        return override

    city = (q.get("city") or "").strip()
    postcode = (q.get("postcode") or "").strip()
    price_q = _price_params(q.get("budget_max"))

    if city:
        slug = _slugify_location(city)
        path = f"/to-rent/property/{slug}/"
        if price_q:
            return f"{_ZOOPLA_ORIGIN}{path}?{urlencode(price_q)}"
        return f"{_ZOOPLA_ORIGIN}{path}"

    if postcode:
        base = f"{_ZOOPLA_ORIGIN}/to-rent/"
        params: dict[str, str] = {
            "search_source": "home",
            "section": "to-rent",
            "q": postcode,
        }
        params.update(price_q)
        return f"{base}?{urlencode(params)}"

    path = "/to-rent/property/london/"
    if price_q:
        return f"{_ZOOPLA_ORIGIN}{path}?{urlencode(price_q)}"
    return f"{_ZOOPLA_ORIGIN}{path}"


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


def _property_type_from_text(summary: str, blob: str) -> str:
    for part in (summary, blob):
        if not part:
            continue
        m = _PROPERTY_TYPE_RE.search(part)
        if m:
            return m.group(1).title()
    return ""


def _bedrooms_from_text(blob: str) -> float:
    if not blob:
        return 0.0
    if re.search(r"\bstudio\b", blob, re.I):
        return 0.0
    m = _BEDS_RE.search(blob)
    if m:
        try:
            return float(m.group(1))
        except ValueError:
            return 0.0
    return 0.0


def _parse_listing_card(
    card: Any,
    page_url: str,
    query: dict[str, Any],
) -> dict[str, Any] | None:
    link = card.select_one('a[href*="/to-rent/details/"]')
    href = link.get("href") if link else None
    if not href:
        return None
    mid = _DETAIL_ID_RE.search(href)
    if not mid:
        return None
    listing_id = mid.group(1)
    source_url = urljoin(page_url, href)

    price_el = card.select_one('[class*="price_priceText"]')
    price_text = price_el.get_text(" ", strip=True) if price_el else ""
    rent_pcm = _parse_pcm(price_text)
    if rent_pcm is None:
        return None

    addr_el = card.select_one('[class*="summary_address"]') or card.select_one("address")
    address = addr_el.get_text(" ", strip=True) if addr_el else ""

    sum_el = card.select_one('[class*="summary_summary"]')
    summary = sum_el.get_text("\n", strip=True) if sum_el else ""

    blob = card.get_text("\n", strip=True)
    bedrooms = _bedrooms_from_text(blob)
    property_type = _property_type_from_text(summary, blob)

    title = (address or (summary.splitlines()[0].strip() if summary else "")) or "Listing"

    city_q = (query.get("city") or "").strip()
    pc_q = (query.get("postcode") or "").strip()
    postcode = _extract_postcode(address, pc_q)
    city = city_q or _guess_city_from_address(address) or "London"
    area_name = _slugify_location(city_q) if city_q else _slugify_location(_postcode_outcode(postcode) or city)

    return {
        "listing_id": listing_id,
        "title": title,
        "address": address,
        "postcode": postcode,
        "area_name": area_name,
        "city": city,
        "rent_pcm": float(rent_pcm),
        "bedrooms": float(bedrooms),
        "property_type": property_type or "Property",
        "source": "zoopla",
        "source_url": source_url,
    }


def _guess_city_from_address(address: str) -> str:
    if not address:
        return ""
    parts = [p.strip() for p in address.split(",") if p.strip()]
    if len(parts) >= 2:
        return parts[-1]
    return ""


def _parse_html_listings(html: str, page_url: str, query: dict[str, Any]) -> list[dict[str, Any]]:
    soup = BeautifulSoup(html, "html.parser")
    scope = soup.select('[data-testid="regular-listings"] [data-testid="listing-card-content"]')
    if not scope:
        scope = soup.select('[data-testid="listing-card-content"]')
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for card in scope:
        row = _parse_listing_card(card, page_url, query)
        if not row:
            continue
        lid = row["listing_id"]
        if lid in seen:
            continue
        seen.add(lid)
        out.append(row)
    return out


def _fetch_live_listings(query: dict[str, Any]) -> list[dict[str, Any]]:
    url = _build_search_url(query)
    r = requests.get(url, headers=_DEFAULT_HEADERS, timeout=20)
    r.raise_for_status()
    final_url = r.url or url
    listings = _parse_html_listings(r.text, final_url, query)
    return listings


def _mock_listings(query: dict[str, Any]) -> list[dict[str, Any]]:
    """Five demo rows in the same spirit as data/ai_demo_listings.json (source=zoopla)."""
    city = (query.get("city") or "").strip() or "London"
    pc = (query.get("postcode") or "").strip() or "E1 6LS"
    slug = _slugify_location(city)
    try:
        budget = int(float(query.get("budget_max"))) if query.get("budget_max") is not None else 1400
    except (TypeError, ValueError):
        budget = 1400

    templates = [
        {
            "listing_id": "90000001",
            "title": f"Modern 1 bed flat, Central {city}",
            "address": f"High Street, {city}",
            "postcode": pc,
            "area_name": slug,
            "city": city,
            "rent_pcm": min(1100.0, float(budget)),
            "bedrooms": 1.0,
            "property_type": "Flat",
        },
        {
            "listing_id": "90000002",
            "title": f"Spacious 2 bed, {city}",
            "address": f"Riverside, {city}",
            "postcode": pc,
            "area_name": slug,
            "city": city,
            "rent_pcm": min(1250.0, float(budget)),
            "bedrooms": 2.0,
            "property_type": "House",
        },
        {
            "listing_id": "90000003",
            "title": f"Studio near centre, {city}",
            "address": f"Market Square, {city}",
            "postcode": pc,
            "area_name": slug,
            "city": city,
            "rent_pcm": min(950.0, float(budget)),
            "bedrooms": 0.0,
            "property_type": "Studio",
        },
        {
            "listing_id": "90000004",
            "title": f"1 bed apartment, {city}",
            "address": f"Station Road, {city}",
            "postcode": pc,
            "area_name": slug,
            "city": city,
            "rent_pcm": min(1050.0, float(budget)),
            "bedrooms": 1.0,
            "property_type": "Apartment",
        },
        {
            "listing_id": "90000005",
            "title": f"2 bed maisonette, {city}",
            "address": f"Park Lane, {city}",
            "postcode": pc,
            "area_name": slug,
            "city": city,
            "rent_pcm": min(1350.0, float(budget)),
            "bedrooms": 2.0,
            "property_type": "Maisonette",
        },
    ]
    base = _ZOOPLA_ORIGIN
    for t in templates:
        t["source"] = "zoopla"
        t["source_url"] = f"{base}/to-rent/details/{t['listing_id']}/"
    return templates


def fetch_zoopla_listings_with_meta(query: dict) -> tuple[list[dict], str]:
    """
    Same as ``fetch_zoopla_listings`` but returns ``(records, source_mode)``:
    ``live_zoopla`` when HTML parse succeeded, else ``zoopla_mock_fallback``.
    """
    q = dict(query or {})
    try:
        rows = _fetch_live_listings(q)
        if rows:
            return rows, "live_zoopla"
    except Exception:
        pass
    return _mock_listings(q), "zoopla_mock_fallback"


def fetch_zoopla_listings(query: dict) -> list[dict]:
    """
    Fetch Zoopla rental listings for a structured query.

    Builds a search URL from ``city`` / ``postcode`` / ``budget_max`` (optional
    ``search_url`` / ``url`` override). Uses HTTP GET + BeautifulSoup. On any
    failure or empty parse, returns five mock listings.
    """
    rows, _ = fetch_zoopla_listings_with_meta(query)
    return rows


__all__ = ["fetch_zoopla_listings", "fetch_zoopla_listings_with_meta"]
