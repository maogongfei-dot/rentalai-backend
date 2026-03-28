"""
Phase D6：多数据源（Zoopla + Rightmove）统一结构与合并拉取。

与 D1–D5 抓取入口兼容：内部仍调用 ``scraper.zoopla_scraper`` / ``scraper.rightmove_scraper``，
本模块在原始 dict 之上提供统一 ``MarketListingUnified`` 与去重键，供 API 或其它服务复用。
"""

from __future__ import annotations

import copy
import logging
import re
from typing import Any, TypedDict

logger = logging.getLogger(__name__)


class MarketListingUnified(TypedDict, total=False):
    """跨平台统一房源视图（扁平 dict，便于 JSON 序列化）。"""

    source: str  # zoopla | rightmove | combined
    source_listing_id: str | None
    source_names: list[str]
    matched_sources: list[dict[str, Any]]
    matched_sources_count: int
    title: str
    price_pcm: float | int | None
    bedrooms: int | None
    bathrooms: int | None
    property_type: str | None
    furnished: str | None
    address: str | None
    area_name: str | None
    postcode: str | None
    latitude: float | None
    longitude: float | None
    listing_url: str | None
    image_url: str | None
    summary: str | None
    added_date: str | None
    provider_raw: dict[str, Any]
    dedupe_key: str | None


def _ensure_dict(raw: Any) -> dict[str, Any]:
    return raw if isinstance(raw, dict) else {}


def _to_float(v: Any) -> float | None:
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        s = re.sub(r"[^\d.\-]", "", v.replace(",", "").replace("£", ""))
        if not s:
            return None
        try:
            return float(s)
        except ValueError:
            return None
    return None


def _to_int(v: Any) -> int | None:
    f = _to_float(v)
    if f is None:
        return None
    try:
        return int(f)
    except (TypeError, ValueError):
        return None


def _simplify_address(addr: str | None) -> str:
    """地址简化串：小写、去空白、去标点，用于去重。"""
    if not addr:
        return ""
    s = re.sub(r"\s+", " ", str(addr).strip().lower())
    return re.sub(r"[^a-z0-9]", "", s)[:120]


def build_listing_dedupe_key(listing: dict[str, Any]) -> str | None:
    """
    稳健去重键：
    1) postcode + price_pcm + bedrooms + 简化 address
    2) 缺 postcode 时：address + price_pcm + bedrooms
    3) 再不行：source + source_listing_id
    """
    pc = (listing.get("postcode") or "").strip().upper()
    price = listing.get("price_pcm")
    price_k = ""
    if price is not None:
        try:
            price_k = f"{float(price):.2f}"
        except (TypeError, ValueError):
            price_k = str(price).strip()

    beds = listing.get("bedrooms")
    beds_k = ""
    if beds is not None:
        try:
            beds_k = str(int(float(beds)))
        except (TypeError, ValueError):
            beds_k = str(beds).strip()

    addr_s = _simplify_address(listing.get("address"))

    if pc and price_k and beds_k and addr_s:
        return f"p:{pc}|£:{price_k}|b:{beds_k}|a:{addr_s}"
    if addr_s and price_k and beds_k:
        return f"a:{addr_s}|£:{price_k}|b:{beds_k}"

    src = str(listing.get("source") or "").strip().lower()
    sid = listing.get("source_listing_id") or listing.get("listing_id")
    if sid is not None and str(sid).strip():
        return f"s:{src}|id:{str(sid).strip()}"
    return None


def _attach_dedupe(out: dict[str, Any]) -> dict[str, Any]:
    out["dedupe_key"] = build_listing_dedupe_key(out)
    return out


def _listing_completeness_score(d: dict[str, Any]) -> int:
    """供 choose_better_listing 使用：信息越完整分越高。"""
    score = 0
    addr = d.get("address")
    if addr:
        score += min(len(str(addr)), 240)
    if (d.get("postcode") or "").strip():
        score += 50
    if (d.get("image_url") or "").strip():
        score += 40
    if (d.get("listing_url") or "").strip():
        score += 30
    if d.get("bedrooms") is not None:
        score += 20
    if d.get("bathrooms") is not None:
        score += 15
    summ = d.get("summary") or ""
    score += min(len(str(summ)), 400)
    return score


def choose_better_listing(a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
    """
    在 dedupe_key 相同的两条中保留信息更完整的一条。
    平局时优先 ``zoopla``，再按 ``source_listing_id`` 字典序稳定决胜。
    """
    sa, sb = _listing_completeness_score(a), _listing_completeness_score(b)
    if sa > sb:
        return a
    if sb > sa:
        return b
    src_a, src_b = str(a.get("source") or ""), str(b.get("source") or "")
    if src_a != src_b:
        if src_a == "zoopla":
            return a
        if src_b == "zoopla":
            return b
        return a if src_a <= src_b else b
    id_a = str(a.get("source_listing_id") or "")
    id_b = str(b.get("source_listing_id") or "")
    return a if id_a >= id_b else b


def _merge_fill_missing(winner: dict[str, Any], other: dict[str, Any]) -> dict[str, Any]:
    """用 other 补全 winner 中缺失的展示字段（不覆盖已有非空值）。"""
    out = copy.deepcopy(winner)
    skip = {
        "provider_raw",
        "dedupe_key",
        "source",
        "matched_sources",
        "source_names",
        "matched_sources_count",
    }
    for k, v in other.items():
        if k in skip:
            continue
        cur = out.get(k)
        if cur in (None, "") and v not in (None, ""):
            out[k] = v
    return out


def _matched_source_entry(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "source": row.get("source"),
        "source_listing_id": row.get("source_listing_id"),
        "listing_url": row.get("listing_url"),
    }


def dedupe_merge_by_key(listings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    按 ``dedupe_key`` 分组；多源命中同键时合并为 ``source=combined``，并写入
    ``source_names`` / ``matched_sources`` / ``matched_sources_count``。
    """
    groups: dict[str, list[dict[str, Any]]] = {}
    order: list[str] = []
    for L in listings:
        k = L.get("dedupe_key")
        if not k:
            k = f"__fallback:{L.get('source')}|{id(L)}"
            L = {**L, "dedupe_key": k}
        if k not in groups:
            order.append(k)
            groups[k] = []
        groups[k].append(L)

    out: list[dict[str, Any]] = []
    for k in order:
        group = groups[k]
        if len(group) == 1:
            row = copy.deepcopy(group[0])
            src = str(row.get("source") or "unknown")
            row["source_names"] = [src]
            row["matched_sources"] = [_matched_source_entry(row)]
            row["matched_sources_count"] = 1
            out.append(row)
            continue

        group_sorted = sorted(group, key=_listing_completeness_score, reverse=True)
        base = copy.deepcopy(group_sorted[0])
        for other in group_sorted[1:]:
            base = _merge_fill_missing(base, other)

        names = sorted({str(x.get("source") or "") for x in group if x.get("source")})
        ms = [_matched_source_entry(x) for x in group]
        base["source"] = "combined"
        base["source_names"] = names
        base["matched_sources"] = ms
        base["matched_sources_count"] = len(ms)
        base["dedupe_key"] = k
        out.append(base)
    return out


def normalize_zoopla_listing(raw: dict[str, Any]) -> dict[str, Any]:
    """Zoopla 原始行 → :class:`MarketListingUnified` 兼容 dict。"""
    r = _ensure_dict(raw)
    raw_copy: dict[str, Any] = copy.deepcopy(r)

    lid = r.get("listing_id") or r.get("id")
    title = (r.get("title") or r.get("heading") or "").strip() or "Listing"
    rent = _to_float(r.get("rent_pcm") or r.get("price") or r.get("rent"))
    beds = _to_int(r.get("bedrooms") or r.get("beds") or r.get("num_bedrooms"))
    baths = _to_int(r.get("bathrooms") or r.get("num_bathrooms"))

    furnished = r.get("furnished_state") or r.get("furnished")
    if furnished is not None and not isinstance(furnished, str):
        furnished = str(furnished)

    out: dict[str, Any] = {
        "source": "zoopla",
        "source_listing_id": str(lid).strip() if lid is not None else None,
        "title": title[:500],
        "price_pcm": rent,
        "bedrooms": beds,
        "bathrooms": baths,
        "property_type": (r.get("property_type") or r.get("category") or None),
        "furnished": furnished if isinstance(furnished, str) else None,
        "address": (r.get("address") or r.get("address_text") or None),
        "area_name": r.get("area_name") or r.get("area"),
        "postcode": (r.get("postcode") or r.get("post_code") or None),
        "latitude": _to_float(r.get("latitude") or r.get("lat")),
        "longitude": _to_float(r.get("longitude") or r.get("lng") or r.get("lon")),
        "listing_url": (r.get("source_url") or r.get("listing_url") or r.get("url") or None),
        "image_url": r.get("image_url") or r.get("image"),
        "summary": r.get("description") or r.get("summary"),
        "added_date": r.get("added_date") or r.get("published"),
        "provider_raw": raw_copy,
    }
    return _attach_dedupe(out)


def normalize_rightmove_listing(raw: dict[str, Any]) -> dict[str, Any]:
    """Rightmove 原始行 → :class:`MarketListingUnified` 兼容 dict。"""
    r = _ensure_dict(raw)
    raw_copy: dict[str, Any] = copy.deepcopy(r)

    lid = r.get("listing_id") or r.get("id")
    title = (r.get("title") or "").strip() or "Listing"
    rent = _to_float(r.get("rent_pcm") or r.get("price") or r.get("rent"))

    beds_raw = r.get("bedrooms")
    beds: int | None
    if isinstance(beds_raw, (int, float)):
        beds = int(float(beds_raw))
    elif isinstance(beds_raw, str):
        beds = _to_int(beds_raw)
    else:
        beds = None

    baths = _to_int(r.get("bathrooms"))

    furnished = r.get("furnished")
    if furnished is not None and not isinstance(furnished, str):
        furnished = str(furnished)

    out: dict[str, Any] = {
        "source": "rightmove",
        "source_listing_id": str(lid).strip() if lid is not None else None,
        "title": title[:500],
        "price_pcm": rent,
        "bedrooms": beds,
        "bathrooms": baths,
        "property_type": r.get("property_type"),
        "furnished": furnished if isinstance(furnished, str) else None,
        "address": r.get("address"),
        "area_name": r.get("area_name"),
        "postcode": r.get("postcode"),
        "latitude": _to_float(r.get("latitude") or r.get("lat")),
        "longitude": _to_float(r.get("longitude") or r.get("lng")),
        "listing_url": (r.get("source_url") or r.get("url") or r.get("listing_url")),
        "image_url": r.get("image_url") or r.get("image"),
        "summary": r.get("summary"),
        "added_date": r.get("added_date"),
        "provider_raw": raw_copy,
    }
    return _attach_dedupe(out)


def _build_scraper_query(
    *,
    location: str | None,
    area: str | None,
    postcode: str | None,
    min_price: float | int | None,
    max_price: float | int | None,
    min_bedrooms: int | float | None,
    max_bedrooms: int | float | None,
    sort_by: str | None,
) -> dict[str, Any]:
    """映射为现有 scraper 使用的 structured_query 风格（city / postcode / budget_max）。"""
    q: dict[str, Any] = {}
    city = (location or area or "").strip()
    if city:
        q["city"] = city
    pc = (postcode or "").strip()
    if pc:
        q["postcode"] = pc
    if max_price is not None:
        try:
            mp = float(max_price)
            q["budget_max"] = mp
            q["_filter_max_price"] = mp
        except (TypeError, ValueError):
            pass
    # min_price / bed 区间 / sort：抓取层多不支持，合并后再过滤
    if min_price is not None:
        try:
            q["_filter_min_price"] = float(min_price)
        except (TypeError, ValueError):
            pass
    if min_bedrooms is not None:
        q["_filter_min_beds"] = float(min_bedrooms)
    if max_bedrooms is not None:
        q["_filter_max_beds"] = float(max_bedrooms)
    if sort_by:
        q["_sort_by"] = str(sort_by).strip().lower()
    return q


def _filter_listings(
    listings: list[dict[str, Any]],
    q: dict[str, Any],
) -> list[dict[str, Any]]:
    mn = q.get("_filter_min_price")
    mx = q.get("_filter_max_price")
    mn_b = q.get("_filter_min_beds")
    mx_b = q.get("_filter_max_beds")
    out: list[dict[str, Any]] = []
    for L in listings:
        p = L.get("price_pcm")
        if mn is not None and p is not None:
            try:
                if float(p) < float(mn):
                    continue
            except (TypeError, ValueError):
                pass
        if mx is not None and p is not None:
            try:
                if float(p) > float(mx):
                    continue
            except (TypeError, ValueError):
                pass
        b = L.get("bedrooms")
        if mn_b is not None and b is not None:
            try:
                if float(b) < float(mn_b):
                    continue
            except (TypeError, ValueError):
                pass
        if mx_b is not None and b is not None:
            try:
                if float(b) > float(mx_b):
                    continue
            except (TypeError, ValueError):
                pass
        out.append(L)
    return out


def _sort_listings(listings: list[dict[str, Any]], sort_by: str | None) -> list[dict[str, Any]]:
    """排序：price_asc/desc、newest、bedrooms_desc 等（与 result 层命名对齐）。"""
    if not sort_by:
        return listings
    key = sort_by.strip().lower()
    if key in ("price_asc", "rent_asc", "pcm_asc"):
        return sorted(
            listings,
            key=lambda x: (x.get("price_pcm") is None, float(x["price_pcm"]) if x.get("price_pcm") is not None else 0.0),
        )
    if key in ("price_desc", "rent_desc", "pcm_desc"):
        return sorted(
            listings,
            key=lambda x: (x.get("price_pcm") is None, -float(x["price_pcm"]) if x.get("price_pcm") is not None else 0.0),
        )
    if key in ("newest", "date_desc", "added_desc"):
        # True = 有日期，优先；同有日期时按字符串降序（ISO 日期可字典序比新旧）
        return sorted(
            listings,
            key=lambda x: (bool(x.get("added_date")), str(x.get("added_date") or "")),
            reverse=True,
        )
    if key in ("bedrooms_desc", "beds_desc"):
        return sorted(
            listings,
            key=lambda x: (
                x.get("bedrooms") is None,
                -float(x["bedrooms"]) if x.get("bedrooms") is not None else 0.0,
            ),
        )
    if key in ("bedrooms_asc", "beds_asc"):
        return sorted(
            listings,
            key=lambda x: (
                x.get("bedrooms") is None,
                float(x["bedrooms"]) if x.get("bedrooms") is not None else 0.0,
            ),
        )
    return listings


def _location_label(
    location: str | None,
    area: str | None,
    postcode: str | None,
) -> str:
    parts = [p for p in [location, area, postcode] if p and str(p).strip()]
    return ", ".join(parts) if parts else ""


def fetch_market_combined(
    *,
    location: str | None = None,
    area: str | None = None,
    postcode: str | None = None,
    min_price: float | int | None = None,
    max_price: float | int | None = None,
    min_bedrooms: int | float | None = None,
    max_bedrooms: int | float | None = None,
    limit: int | None = None,
    sort_by: str | None = None,
) -> dict[str, Any]:
    """
    并行拉取 Zoopla + Rightmove，统一 normalize，合并、过滤、排序、去重。

    单源失败时写入 ``errors``，不影响另一源。
    """
    from scraper.rightmove_scraper import fetch_rightmove_listings
    from scraper.zoopla_scraper import fetch_zoopla_listings

    q = _build_scraper_query(
        location=location,
        area=area,
        postcode=postcode,
        min_price=min_price,
        max_price=max_price,
        min_bedrooms=min_bedrooms,
        max_bedrooms=max_bedrooms,
        sort_by=sort_by,
    )

    scraper_q = {k: v for k, v in q.items() if not str(k).startswith("_filter") and k != "_sort_by"}
    errors: dict[str, str] = {}

    raw_z: list[dict[str, Any]] = []
    try:
        raw_z = fetch_zoopla_listings(scraper_q)
        logger.info("market_combined: zoopla raw_count=%s", len(raw_z))
    except Exception as exc:
        errors["zoopla"] = str(exc)
        logger.warning("market_combined: zoopla failed: %s", exc)

    raw_r: list[dict[str, Any]] = []
    try:
        raw_r = fetch_rightmove_listings(scraper_q)
        logger.info("market_combined: rightmove raw_count=%s", len(raw_r))
    except Exception as exc:
        errors["rightmove"] = str(exc)
        logger.warning("market_combined: rightmove failed: %s", exc)

    unified: list[dict[str, Any]] = []
    for row in raw_z:
        try:
            unified.append(normalize_zoopla_listing(row))
        except Exception as exc:
            logger.debug("market_combined: skip bad zoopla row: %s", exc)
    for row in raw_r:
        try:
            unified.append(normalize_rightmove_listing(row))
        except Exception as exc:
            logger.debug("market_combined: skip bad rightmove row: %s", exc)

    unified = _filter_listings(unified, q)
    total_before = len(unified)
    deduped = dedupe_merge_by_key(unified)
    total_after = len(deduped)
    deduped = _sort_listings(deduped, q.get("_sort_by") or sort_by)

    if limit is not None and limit > 0:
        deduped = deduped[: int(limit)]

    loc = _location_label(location, area, postcode)
    sources_used: list[str] = []
    if raw_z:
        sources_used.append("zoopla")
    if raw_r:
        sources_used.append("rightmove")

    success = total_after > 0 or not errors

    return {
        "success": success,
        "location": loc or None,
        "total_before_dedupe": total_before,
        "total_after_dedupe": total_after,
        "sources_used": sources_used,
        "listings": deduped,
        "errors": errors,
    }


# 别名（任务 D6-2 命名）
get_combined_market_listings = fetch_market_combined


__all__ = [
    "MarketListingUnified",
    "build_listing_dedupe_key",
    "choose_better_listing",
    "dedupe_merge_by_key",
    "fetch_market_combined",
    "get_combined_market_listings",
    "normalize_rightmove_listing",
    "normalize_zoopla_listing",
]


def _cli_main() -> None:
    """最小调试：``python -m services.market_combined London``"""
    import json
    import sys

    loc = (sys.argv[1] if len(sys.argv) > 1 else "London").strip()
    r = fetch_market_combined(location=loc, max_price=2500, limit=8, sort_by="price_asc")
    print(json.dumps(r, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    _cli_main()
