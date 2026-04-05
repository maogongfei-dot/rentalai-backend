"""
Phase 2: Rightmove single-listing parser (requests + BeautifulSoup).

Standalone module — not wired to chat/router. Extend later for multi-page / Playwright.

Dependencies: pip install requests beautifulsoup4
"""

from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup, Tag

_DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-GB,en;q=0.9",
}

_BED_RE = re.compile(
    r"(\d+)\s*(?:bed(?:room)?s?|br\b)",
    re.I,
)
_BATH_RE = re.compile(
    r"(\d+)\s*bath(?:room)?s?",
    re.I,
)
_PRICE_PCM_RE = re.compile(
    r"£\s*([\d,]+(?:\.\d+)?)\s*(?:pcm|p\.c\.m\.|per\s*month|/month|a\s*month)?",
    re.I,
)
_PRICE_ANY_RE = re.compile(r"£\s*([\d,]+(?:\.\d+)?)")
_PROPERTY_TYPE_RE = re.compile(
    r"\b(flat|apartment|house|bungalow|studio|maisonette|cottage|penthouse|detached|terraced)\b",
    re.I,
)

# Regex hints on raw HTML (embedded JSON fragments)
_HTML_PRICE_HINTS = (
    re.compile(r'"price":\s*"?(\d+)"?', re.I),
    re.compile(r'"pricePerMonth":\s*(\d+)', re.I),
    re.compile(r'"rent":\s*(\d+)', re.I),
    re.compile(r'"amount":\s*(\d+)', re.I),
    re.compile(r'"formattedPrice":\s*"£([\d,]+)', re.I),
)
_HTML_BED_HINTS = (
    re.compile(r'"bedrooms":\s*(\d+)', re.I),
    re.compile(r'"beds":\s*(\d+)', re.I),
    re.compile(r'"numberOfBedrooms":\s*(\d+)', re.I),
)
_HTML_BATH_HINTS = (
    re.compile(r'"bathrooms":\s*(\d+)', re.I),
    re.compile(r'"numberOfBathrooms":\s*(\d+)', re.I),
)
_MEDIA_IMG_RE = re.compile(
    r"https://media\.rightmove\.co\.uk/[^\s\"'<>]+",
    re.I,
)


def safe_get_text(node: Any) -> str | None:
    """Safely get stripped text from a Tag/string; missing node → None."""
    if node is None:
        return None
    try:
        if isinstance(node, Tag) or hasattr(node, "get_text"):
            t = node.get_text(separator=" ", strip=True)
        else:
            t = str(node).strip()
        t = " ".join(t.split()) if t else ""
        return t if t else None
    except Exception:
        return None


def clean_price(price_text: str | None) -> int | None:
    """Parse a price string to int monthly rent, e.g. '£1,200 pcm' -> 1200; fail → None."""
    if not price_text:
        return None
    s = str(price_text).strip()
    m = _PRICE_PCM_RE.search(s) or _PRICE_ANY_RE.search(s)
    if not m:
        digits = re.sub(r"[^\d]", "", s.split(".")[0])
        return int(digits) if digits else None
    num = m.group(1).replace(",", "")
    try:
        return int(float(num))
    except (TypeError, ValueError):
        return None


def extract_number(text: str | None, *, kind: str = "any") -> int | None:
    """
    Extract a leading integer from phrases like '2 bed', '1 bathroom'.
    kind: 'bed' | 'bath' | 'any' (bed first, then bath, then first plausible digit).
    """
    if not text:
        return None
    s = str(text).strip()
    try:
        if kind in ("bed", "bedroom", "any"):
            m = _BED_RE.search(s)
            if m:
                return int(m.group(1))
        if kind in ("bath", "bathroom", "any"):
            m = _BATH_RE.search(s)
            if m:
                return int(m.group(1))
        if kind == "any":
            m = re.search(r"\b(\d+)\b", s)
            if m:
                return int(m.group(1))
    except (TypeError, ValueError):
        return None
    return None


def first_non_empty(*values: Any) -> Any:
    """Return the first non-empty value (None / blank str / empty list / empty dict skipped)."""
    for v in values:
        if v is None:
            continue
        if isinstance(v, str) and not v.strip():
            continue
        if isinstance(v, (list, dict)) and len(v) == 0:
            continue
        return v
    return None


def safe_text(node: Any, default: str | None = None) -> str | None:
    """Compatibility: same as safe_get_text with optional default."""
    t = safe_get_text(node)
    return t if t is not None else default


def _is_rightmove_url(url: str) -> bool:
    try:
        host = urlparse(url).netloc.lower()
        return "rightmove.co.uk" in host
    except Exception:
        return False


def _collect_ld_json(soup: BeautifulSoup) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for tag in soup.find_all("script", type="application/ld+json"):
        raw = tag.string or tag.get_text() or ""
        raw = raw.strip()
        if not raw:
            continue
        try:
            data = json.loads(raw)
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        out.append(item)
            elif isinstance(data, dict):
                out.append(data)
        except json.JSONDecodeError:
            continue
    return out


def _extract_regex_hints_from_html(html: str) -> dict[str, Any]:
    """Pull price/bed/bath from raw HTML when JSON is embedded as text."""
    out: dict[str, Any] = {}
    if not html:
        return out
    for rx in _HTML_PRICE_HINTS:
        m = rx.search(html)
        if m:
            try:
                raw = m.group(1).replace(",", "")
                out["price_int"] = int(raw)
                break
            except (ValueError, IndexError):
                continue
    for rx in _HTML_BED_HINTS:
        m = rx.search(html)
        if m:
            try:
                out["bedrooms"] = int(m.group(1))
                break
            except (ValueError, IndexError):
                continue
    for rx in _HTML_BATH_HINTS:
        m = rx.search(html)
        if m:
            try:
                out["bathrooms"] = int(m.group(1))
                break
            except (ValueError, IndexError):
                continue
    return out


def _extract_json_script_blocks(soup: BeautifulSoup) -> list[Any]:
    """Parse inline JSON from script tags (__NEXT_DATA__, application/json, large JSON blobs)."""
    parsed: list[Any] = []
    for tag in soup.find_all("script"):
        try:
            sid = (tag.get("id") or "").strip()
            typ = (tag.get("type") or "").strip().lower()
            raw = tag.string or tag.get_text() or ""
            raw = raw.strip()
            if not raw:
                continue
            if sid == "__NEXT_DATA__" or typ == "application/json" or (
                len(raw) > 80 and raw[0] in "{["
            ):
                try:
                    parsed.append(json.loads(raw))
                except json.JSONDecodeError:
                    continue
        except Exception:
            continue
    return parsed


def _walk_dict_for_numbers(obj: Any, depth: int = 0) -> dict[str, Any]:
    found: dict[str, Any] = {}
    if depth > 14:
        return found
    if isinstance(obj, dict):
        lower_keys = {str(k).lower(): (k, v) for k, v in obj.items()}
        for lk, (k, v) in lower_keys.items():
            if any(n in lk for n in ("price", "rent", "amount", "pcm")):
                if isinstance(v, (int, float)) and 0 < v < 10_000_000:
                    found.setdefault("price_num", int(v))
                elif isinstance(v, str):
                    pi = clean_price(v)
                    if pi is not None:
                        found.setdefault("price_num", pi)
            if any(n in lk for n in ("bedrooms", "beds", "bedroom", "numberofbedrooms")):
                if isinstance(v, (int, float)):
                    found.setdefault("bedrooms", int(v))
                elif isinstance(v, str):
                    n = extract_number(v, kind="bed")
                    if n is not None:
                        found.setdefault("bedrooms", n)
            if any(n in lk for n in ("bathrooms", "baths", "bathroom", "numberofbathrooms")):
                if isinstance(v, (int, float)):
                    found.setdefault("bathrooms", int(v))
                elif isinstance(v, str):
                    n = extract_number(v, kind="bath")
                    if n is not None:
                        found.setdefault("bathrooms", n)
            if lk in ("propertytype", "property_type", "type") and isinstance(v, str):
                m = _PROPERTY_TYPE_RE.search(v)
                if m:
                    found.setdefault("property_type", m.group(1).lower())
        for v in obj.values():
            found.update(_walk_dict_for_numbers(v, depth + 1))
    elif isinstance(obj, list):
        for item in obj[:80]:
            found.update(_walk_dict_for_numbers(item, depth + 1))
    return found


def _merge_script_trees(trees: list[Any]) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for tree in trees:
        merged.update(_walk_dict_for_numbers(tree))
    return merged


def _extract_from_ld_json(items: list[dict[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {"images_extra": []}
    for item in items:
        if not isinstance(item, dict):
            continue
        scanned = _walk_dict_for_numbers(item)
        if scanned.get("price_num") is not None:
            out.setdefault("price_int", scanned["price_num"])
        if scanned.get("bedrooms") is not None:
            out.setdefault("bedrooms", scanned["bedrooms"])
        if scanned.get("bathrooms") is not None:
            out.setdefault("bathrooms", scanned["bathrooms"])
        if scanned.get("property_type"):
            out.setdefault("property_type", scanned["property_type"])

        name = item.get("name") or item.get("headline")
        if name and not out.get("title"):
            out["title"] = safe_get_text(name)
        desc = item.get("description")
        if desc and not out.get("description"):
            out["description"] = safe_get_text(desc)
        addr = item.get("address")
        if isinstance(addr, dict):
            parts = [
                addr.get("streetAddress"),
                addr.get("addressLocality"),
                addr.get("addressRegion"),
                addr.get("postalCode"),
            ]
            line = ", ".join(safe_get_text(p) for p in parts if safe_get_text(p))
            if line:
                out.setdefault("address", line)
        offers = item.get("offers")
        if isinstance(offers, dict):
            price = offers.get("price") or offers.get("lowPrice") or offers.get("highPrice")
            if isinstance(price, (int, float)):
                out.setdefault("price_int", int(price))
            elif isinstance(price, str):
                pi = clean_price(price)
                if pi is not None:
                    out.setdefault("price_int", pi)
        img = item.get("image")
        if img:
            extra: list[str] = out["images_extra"]
            if isinstance(img, str):
                extra.append(img)
            elif isinstance(img, list):
                extra.extend(str(x) for x in img if x)
        num_rooms = item.get("numberOfRooms")
        if isinstance(num_rooms, (int, float)) and out.get("bedrooms") is None:
            out.setdefault("bedrooms", int(num_rooms))

        cat = item.get("category")
        if isinstance(cat, str) and not out.get("property_type"):
            m = _PROPERTY_TYPE_RE.search(cat)
            if m:
                out["property_type"] = m.group(1).lower()
    return out


def _try_next_data(soup: BeautifulSoup) -> dict[str, Any]:
    out: dict[str, Any] = {}
    tag = soup.find("script", id="__NEXT_DATA__")
    if not tag:
        return out
    raw = tag.string or tag.get_text() or ""
    raw = raw.strip()
    if not raw:
        return out
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return out
    scanned = _walk_dict_for_numbers(data)
    if scanned.get("price_num") is not None:
        out["price_int"] = scanned["price_num"]
    if scanned.get("bedrooms") is not None:
        out["bedrooms"] = scanned["bedrooms"]
    if scanned.get("bathrooms") is not None:
        out["bathrooms"] = scanned["bathrooms"]
    if scanned.get("property_type"):
        out["property_type"] = scanned["property_type"]
    return out


def _regex_counts_from_text(text: str) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if not text:
        return out
    nbed = extract_number(text, kind="bed")
    if nbed is not None:
        out["bedrooms"] = nbed
    nbath = extract_number(text, kind="bath")
    if nbath is not None:
        out["bathrooms"] = nbath
    pm = _PRICE_PCM_RE.search(text) or _PRICE_ANY_RE.search(text)
    if pm:
        pi = clean_price(pm.group(0))
        if pi is not None:
            out["price_int"] = pi
    ptm = _PROPERTY_TYPE_RE.search(text)
    if ptm:
        out["property_type"] = ptm.group(1).lower()
    return out


def _html_selectors_price(soup: BeautifulSoup) -> int | None:
    selectors = (
        '[class*="PropertyPrice"]',
        '[class*="price"]',
        '[data-test*="price"]',
        "[itemprop=price]",
    )
    for sel in selectors:
        try:
            el = soup.select_one(sel)
        except Exception:
            el = None
        if not el:
            continue
        t = safe_get_text(el)
        if t:
            p = clean_price(t)
            if p is not None:
                return p
    return None


def _html_selectors_address(soup: BeautifulSoup) -> str | None:
    for sel in (
        '[class*="Address"]',
        '[class*="address"]',
        "[itemprop=streetAddress]",
        '[class*="propertyHeader"] h1',
        "h1",
    ):
        try:
            el = soup.select_one(sel)
        except Exception:
            el = None
        if not el:
            continue
        t = safe_get_text(el)
        if t and len(t) > 8:
            return t
    meta = soup.find("meta", property="og:title")
    if meta and meta.get("content"):
        t = safe_get_text(meta.get("content"))
        if t:
            return t
    return None


def _html_selectors_description(soup: BeautifulSoup) -> str | None:
    for sel in (
        '[class*="Description"]',
        '[class*="description"]',
        '[class*="About"]',
        "article",
        "main",
    ):
        try:
            el = soup.select_one(sel)
        except Exception:
            el = None
        if not el:
            continue
        t = safe_get_text(el)
        if t and len(t) > 120:
            return t[:20000]
    return None


def _html_selectors_property_details(soup: BeautifulSoup) -> dict[str, Any]:
    """Key features / info strip: text used for bed/bath/type."""
    out: dict[str, Any] = {}
    chunks: list[str] = []
    for sel in (
        '[class*="PropertyInformation"]',
        '[class*="KeyFeatures"]',
        '[class*="keyFeatures"]',
        '[class*="Features"]',
        '[class*="propertyInformation"]',
    ):
        try:
            for el in soup.select(sel)[:5]:
                t = safe_get_text(el)
                if t:
                    chunks.append(t)
        except Exception:
            continue
    blob = " ".join(chunks)[:12000]
    if blob:
        out.update(_regex_counts_from_text(blob))
    return out


def _html_fallback(soup: BeautifulSoup, base_url: str) -> dict[str, Any]:
    out: dict[str, Any] = {}
    h1 = soup.find("h1")
    if h1:
        out["heading"] = safe_get_text(h1)
    og_title = soup.find("meta", property="og:title")
    if og_title and og_title.get("content"):
        out.setdefault("og_title", safe_get_text(og_title.get("content")))
    og_desc = soup.find("meta", property="og:description")
    if og_desc and og_desc.get("content"):
        out.setdefault("og_description", safe_get_text(og_desc.get("content")))

    for sel in (
        '[class*="PropertyInformation"]',
        '[class*="propertyHeader"]',
        '[class*="_price"]',
        "article",
        "main",
    ):
        try:
            block = soup.select_one(sel)
        except Exception:
            block = None
        if block:
            t = safe_get_text(block)
            if t and len(t) > 20:
                merged = _regex_counts_from_text(t)
                out.update({k: v for k, v in merged.items() if k not in out})
            break

    seen: set[str] = set()
    images: list[str] = []
    for img in soup.find_all("img"):
        for attr in ("src", "data-src", "data-original", "data-lazy"):
            src = img.get(attr)
            if not src or not isinstance(src, str):
                continue
            src = src.strip().split()[0] if src else ""
            if not src.startswith("http"):
                src = urljoin(base_url, src)
            low = src.lower()
            if "rightmove" not in low and "media" not in low:
                continue
            if src in seen:
                continue
            seen.add(src)
            images.append(src)
            if len(images) >= 50:
                break
        if len(images) >= 50:
            break
    if images:
        out["images"] = images
    return out


def _urls_from_raw_html(html: str) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for m in _MEDIA_IMG_RE.finditer(html or ""):
        u = m.group(0).rstrip("\\\"'")
        if u not in seen:
            seen.add(u)
            out.append(u)
        if len(out) >= 40:
            break
    return out


def _visible_body_text(soup: BeautifulSoup) -> str:
    """Main visible text for raw_text (scripts/styles removed)."""
    try:
        soup2 = BeautifulSoup(str(soup), "html.parser")
        for bad in soup2(["script", "style", "noscript", "svg"]):
            try:
                bad.decompose()
            except Exception:
                continue
        body = soup2.find("body")
        blob = safe_get_text(body) if body else safe_get_text(soup2)
        if blob:
            return blob[:200000]
    except Exception:
        pass
    return ""


def _merge_description(*parts: str | None) -> str | None:
    texts = [p.strip() for p in parts if p and str(p).strip()]
    if not texts:
        return None
    return "\n\n".join(dict.fromkeys(texts))


def build_empty_result(url: str) -> dict[str, Any]:
    """Fixed-shape payload for parse_rightmove_listing (defaults + status shell)."""
    u = (url or "").strip()
    return {
        "platform": "rightmove",
        "url": u,
        "price": None,
        "address": None,
        "bedrooms": None,
        "bathrooms": None,
        "property_type": None,
        "description": None,
        "images": [],
        "raw_text": "",
        "status": "partial",
        "error": None,
    }


def _normalize_listing_result(result: dict[str, Any]) -> dict[str, Any]:
    """Strip strings, empty str → None for text fields; clean images; raw_text always str."""
    desc = result.get("description")
    if isinstance(desc, str) and not desc.strip():
        result["description"] = None
    for key in ("address", "property_type"):
        v = result.get(key)
        if v is None:
            continue
        if isinstance(v, str):
            s = v.strip()
            result[key] = s if s else None
        else:
            s = str(v).strip()
            result[key] = s if s else None

    imgs = result.get("images")
    if not isinstance(imgs, list):
        imgs = []
    seen: set[str] = set()
    clean_imgs: list[str] = []
    for x in imgs:
        if not x or not isinstance(x, str):
            continue
        s = x.strip()
        if not s or s in seen:
            continue
        seen.add(s)
        clean_imgs.append(s)
    result["images"] = clean_imgs

    rt = result.get("raw_text")
    if rt is None:
        result["raw_text"] = ""
    elif not isinstance(rt, str):
        result["raw_text"] = str(rt)

    return result


def _apply_parse_status(result: dict[str, Any]) -> None:
    """Set status to success or partial when not already error."""
    if result.get("status") == "error":
        return
    core = sum(
        1 for k in ("price", "address", "description") if result.get(k) is not None
    )
    if core >= 2:
        result["status"] = "success"
    else:
        result["status"] = "partial"
    result["error"] = None


def parse_rightmove_listing(url: str) -> dict[str, Any]:
    """
    Fetch a single Rightmove property page and return structured fields.

    Order: JSON / embedded script data → regex hints on HTML → HTML selectors → None.
    Does not raise on failure; returns unified dict with status/error and normalized fields.
    """
    result = build_empty_result(url)
    u = result["url"]
    if not u or not _is_rightmove_url(u):
        result["status"] = "error"
        result["error"] = "Invalid or empty Rightmove URL"
        return _normalize_listing_result(result)

    try:
        r = requests.get(u, headers=_DEFAULT_HEADERS, timeout=25)
        r.raise_for_status()
        html = r.text or ""

        soup = BeautifulSoup(html, "html.parser")
        # Snapshot visible text before any soup mutation (description path decomposes scripts).
        visible_snapshot = _visible_body_text(BeautifulSoup(html, "html.parser"))

        ld_items = _collect_ld_json(soup)
        ld_out = _extract_from_ld_json(ld_items)
        script_trees = _extract_json_script_blocks(soup)
        script_merged = _merge_script_trees(script_trees)
        next_out = _try_next_data(soup)
        regex_html = _extract_regex_hints_from_html(html)

        body_text = ""
        try:
            body = soup.find("body")
            body_text = safe_get_text(body) or ""
        except Exception:
            body_text = ""

        merged_regex = _regex_counts_from_text(body_text)
        details_strip = _html_selectors_property_details(soup)
        fallback = _html_fallback(soup, u)

        price_val = first_non_empty(
            ld_out.get("price_int"),
            next_out.get("price_int"),
            script_merged.get("price_num"),
            regex_html.get("price_int"),
            merged_regex.get("price_int"),
            details_strip.get("price_int"),
            fallback.get("price_int"),
            _html_selectors_price(soup),
        )
        if price_val is not None:
            try:
                result["price"] = int(price_val)
            except (TypeError, ValueError):
                result["price"] = None

        beds = first_non_empty(
            ld_out.get("bedrooms"),
            next_out.get("bedrooms"),
            script_merged.get("bedrooms"),
            regex_html.get("bedrooms"),
            merged_regex.get("bedrooms"),
            details_strip.get("bedrooms"),
            fallback.get("bedrooms"),
        )
        if beds is None and body_text:
            beds = extract_number(body_text[:5000], kind="bed")
        if beds is not None:
            try:
                result["bedrooms"] = int(beds)
            except (TypeError, ValueError):
                pass

        baths = first_non_empty(
            ld_out.get("bathrooms"),
            next_out.get("bathrooms"),
            script_merged.get("bathrooms"),
            regex_html.get("bathrooms"),
            merged_regex.get("bathrooms"),
            details_strip.get("bathrooms"),
            fallback.get("bathrooms"),
        )
        if baths is None and body_text:
            baths = extract_number(body_text[:5000], kind="bath")
        if baths is not None:
            try:
                result["bathrooms"] = int(baths)
            except (TypeError, ValueError):
                pass

        addr = first_non_empty(
            ld_out.get("address"),
            _html_selectors_address(soup),
            safe_get_text(soup.find("address")),
            fallback.get("heading"),
        )
        if not addr:
            try:
                meta_addr = soup.find("meta", attrs={"name": re.compile(r"location|address", re.I)})
                if meta_addr and meta_addr.get("content"):
                    addr = safe_get_text(meta_addr.get("content"))
            except Exception:
                pass
        result["address"] = addr

        ptype = first_non_empty(
            ld_out.get("property_type"),
            next_out.get("property_type"),
            script_merged.get("property_type"),
            merged_regex.get("property_type"),
            details_strip.get("property_type"),
            fallback.get("property_type"),
        )
        if not ptype and body_text:
            pm = _PROPERTY_TYPE_RE.search(body_text[:4000])
            if pm:
                ptype = pm.group(1).lower()
        result["property_type"] = ptype

        desc = _merge_description(
            ld_out.get("description"),
            fallback.get("og_description"),
        )
        if not desc:
            desc = fallback.get("og_description")
        if not desc:
            desc = _html_selectors_description(soup)
        if not desc:
            try:
                for bad in soup(["script", "style", "noscript"]):
                    bad.decompose()
                main = soup.find("main") or soup.find("article") or soup.body
                blob = safe_get_text(main) if main else safe_get_text(soup)
                if blob and len(blob) > 80:
                    desc = blob[:15000]
            except Exception:
                desc = None
        result["description"] = desc

        imgs: list[str] = list(ld_out.get("images_extra") or [])
        for im in fallback.get("images") or []:
            if im and im not in imgs:
                imgs.append(im)
        for im in _urls_from_raw_html(html):
            if im not in imgs:
                imgs.append(im)
        seen_i: set[str] = set()
        deduped: list[str] = []
        for im in imgs:
            if im in seen_i:
                continue
            seen_i.add(im)
            deduped.append(im)
        result["images"] = deduped[:60]

        result["raw_text"] = visible_snapshot if visible_snapshot else (html[:200000] if html else "")

        _normalize_listing_result(result)
        _apply_parse_status(result)
        return result
    except Exception as exc:
        err = build_empty_result(url)
        err["status"] = "error"
        msg = str(exc).strip() or "Request or parse failed"
        err["error"] = msg[:500]
        return _normalize_listing_result(err)


if __name__ == "__main__":
    # Phase 2 Part 2: local test — replace with a real listing URL to verify parsing.
    test_url = "https://www.rightmove.co.uk/properties/placeholder"

    result = parse_rightmove_listing(test_url)

    print("Price:", result.get("price"))
    print("Address:", result.get("address"))
    print("Bedrooms:", result.get("bedrooms"))

    description = result.get("description") or ""
    print("Description:", description[:100])

    images = result.get("images") or []
    print("Images count:", len(images))
    print("Status:", result.get("status"))
    print("Error:", result.get("error"))
