"""
Phase D7：市场结论引擎 —— 在 D6 ``get_combined_market_listings`` 结果上做汇总与轻量分析。
"""

from __future__ import annotations

import copy
import logging
from collections import Counter
from statistics import median
from typing import Any

logger = logging.getLogger(__name__)


def _to_float(v: Any) -> float | None:
    if v is None or isinstance(v, bool):
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _bed_sort_key(k: str) -> float:
    try:
        return float(k)
    except (TypeError, ValueError):
        return 0.0


def _to_bedrooms_key(v: Any) -> str | None:
    if v is None:
        return None
    try:
        f = float(v)
        if f < 0:
            return None
        if f == 0:
            return "0"
        return str(int(f)) if f == int(f) else str(round(f, 1))
    except (TypeError, ValueError):
        return None


def _clean_listing_for_json(row: dict[str, Any]) -> dict[str, Any]:
    """浅拷贝，保证可 JSON 序列化（不递归 provider_raw 中的不可序列化对象）。"""
    out = dict(row)
    if "provider_raw" in out and isinstance(out["provider_raw"], dict):
        try:
            out["provider_raw"] = copy.deepcopy(out["provider_raw"])
        except Exception:
            out["provider_raw"] = {}
    return out


def analyze_price_bands(listings: list[dict[str, Any]]) -> dict[str, Any]:
    """
    价格带计数与主导带。
    """
    bands = {
        "under_1000": 0,
        "1000_1499": 0,
        "1500_1999": 0,
        "2000_2499": 0,
        "2500_plus": 0,
    }
    for L in listings:
        p = _to_float(L.get("price_pcm"))
        if p is None:
            continue
        if p < 1000:
            bands["under_1000"] += 1
        elif p < 1500:
            bands["1000_1499"] += 1
        elif p < 2000:
            bands["1500_1999"] += 1
        elif p < 2500:
            bands["2000_2499"] += 1
        else:
            bands["2500_plus"] += 1

    dominant = None
    if any(bands.values()):
        dominant = max(bands, key=lambda k: bands[k])

    summary_parts = [f"{k.replace('_', ' ')}: {v}" for k, v in bands.items() if v]
    price_band_summary = (
        "Distribution across pcm bands — " + "; ".join(summary_parts) if summary_parts else "No priced listings."
    )

    return {
        "budget_band_counts": bands,
        "dominant_price_band": dominant,
        "price_band_summary": price_band_summary,
    }


def analyze_bedroom_price_map(listings: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """
    每个卧室数档位：条数、均价、最低、最高（忽略无价行）。
    """
    by_bed: dict[str, list[float]] = {}
    for L in listings:
        bk = _to_bedrooms_key(L.get("bedrooms"))
        p = _to_float(L.get("price_pcm"))
        if bk is None or p is None:
            continue
        by_bed.setdefault(bk, []).append(p)

    out: dict[str, dict[str, Any]] = {}
    for k, prices in sorted(by_bed.items(), key=lambda x: _bed_sort_key(x[0])):
        if not prices:
            continue
        out[k] = {
            "count": len(prices),
            "avg_price": round(sum(prices) / len(prices), 2),
            "min_price": round(min(prices), 2),
            "max_price": round(max(prices), 2),
        }
    return out


def analyze_value_candidates(listings: list[dict[str, Any]], *, top_n: int = 5) -> list[dict[str, Any]]:
    """
    简单性价比：低于均价、有卧室、有地址信息；按 bedrooms/price_pcm 降序。
    """
    prices = [_to_float(L.get("price_pcm")) for L in listings]
    prices = [p for p in prices if p is not None and p > 0]
    if not prices:
        return []
    avg_p = sum(prices) / len(prices)

    scored: list[tuple[float, dict[str, Any]]] = []
    for L in listings:
        p = _to_float(L.get("price_pcm"))
        b = _to_float(L.get("bedrooms"))
        if p is None or p <= 0 or b is None:
            continue
        if p >= avg_p:
            continue
        addr_ok = bool((L.get("postcode") or "").strip()) or bool((L.get("address") or "").strip())
        if not addr_ok:
            continue
        ratio = b / p
        slim = {
            "title": L.get("title"),
            "price_pcm": p,
            "bedrooms": b,
            "source": L.get("source"),
            "listing_url": L.get("listing_url"),
            "postcode": L.get("postcode"),
            "value_ratio": round(ratio * 1000, 4),
        }
        scored.append((ratio, slim))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [x[1] for x in scored[:top_n]]


def _build_basic_stats(listings: list[dict[str, Any]], sources_used: list[str]) -> dict[str, Any]:
    total = len(listings)
    prices: list[float] = []
    beds: list[float] = []
    bedroom_dist: Counter[str] = Counter()
    prop_type_dist: Counter[str] = Counter()
    postcode_dist: Counter[str] = Counter()
    furn_dist: Counter[str] = Counter()
    with_img = 0
    with_pc = 0
    with_coord = 0

    for L in listings:
        p = _to_float(L.get("price_pcm"))
        if p is not None:
            prices.append(p)

        bk = _to_bedrooms_key(L.get("bedrooms"))
        if bk is not None:
            bedroom_dist[bk] += 1
            try:
                beds.append(float(bk))
            except ValueError:
                pass

        pt = L.get("property_type")
        if pt and str(pt).strip():
            prop_type_dist[str(pt).strip()] += 1
        else:
            prop_type_dist["(unknown)"] += 1

        pc = (L.get("postcode") or "").strip().upper()
        if pc:
            postcode_dist[pc] += 1
            with_pc += 1

        fu = L.get("furnished")
        if fu is not None and str(fu).strip():
            furn_dist[str(fu).strip().lower()] += 1
        else:
            furn_dist["(unknown)"] += 1

        if (L.get("image_url") or "").strip():
            with_img += 1

        lat = _to_float(L.get("latitude"))
        lng = _to_float(L.get("longitude"))
        if lat is not None and lng is not None:
            with_coord += 1

    avg_price = round(sum(prices) / len(prices), 2) if prices else None
    med_price = round(median(prices), 2) if prices else None
    min_p = round(min(prices), 2) if prices else None
    max_p = round(max(prices), 2) if prices else None
    avg_beds = round(sum(beds) / len(beds), 2) if beds else None

    top_pc = [list(x) for x in postcode_dist.most_common(10)]
    postcode_top = [{"postcode": a, "count": b} for a, b in top_pc]

    return {
        "total_listings": total,
        "sources_used": list(sources_used),
        "average_price_pcm": avg_price,
        "median_price_pcm": med_price,
        "min_price_pcm": min_p,
        "max_price_pcm": max_p,
        "average_bedrooms": avg_beds,
        "bedroom_distribution": dict(sorted(bedroom_dist.items(), key=lambda x: _bed_sort_key(x[0]))),
        "property_type_distribution": dict(prop_type_dist.most_common()),
        "postcode_distribution_top": postcode_top,
        "furnished_distribution": dict(furn_dist.most_common()),
        "listings_with_images": with_img,
        "listings_with_postcode": with_pc,
        "listings_with_coordinates": with_coord,
    }


def _overall_analysis(
    stats: dict[str, Any],
    bedroom_dist: dict[str, int],
    price_bands: dict[str, Any],
) -> dict[str, Any]:
    n = int(stats.get("total_listings") or 0)
    med = stats.get("median_price_pcm")

    if med is None:
        m_level = "medium"
    else:
        if med < 1000:
            m_level = "low"
        elif med < 1600:
            m_level = "medium"
        else:
            m_level = "high"

    if n < 5:
        supply = "low"
    elif n < 25:
        supply = "medium"
    else:
        supply = "high"

    focus = None
    if bedroom_dist:
        focus = max(bedroom_dist, key=lambda k: bedroom_dist[k])

    dom = price_bands.get("dominant_price_band")
    msg = (
        f"Sample median pcm ~{med if med is not None else 'n/a'}; "
        f"dominant band: {dom or 'n/a'}; "
        f"most common bedroom count: {focus or 'n/a'}."
    )

    return {
        "market_price_level": m_level,
        "supply_level": supply,
        "bedroom_focus": focus,
        "value_message": msg.strip(),
    }


def get_market_insight(
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
    拉取合并列表（D6）并生成统计 + 价格带/卧室性价比/总览结论。

    ``listings`` 为去重后结果（与 D6 一致），便于下游继续分析。
    """
    from services.market_combined import get_combined_market_listings

    combined = get_combined_market_listings(
        location=location,
        area=area,
        postcode=postcode,
        min_price=min_price,
        max_price=max_price,
        min_bedrooms=min_bedrooms,
        max_bedrooms=max_bedrooms,
        limit=limit,
        sort_by=sort_by,
    )

    listings = [x for x in (combined.get("listings") or []) if isinstance(x, dict)]
    sources_used = list(combined.get("sources_used") or [])
    errors = dict(combined.get("errors") or {})

    if not listings:
        empty_stats = {
            "total_listings": 0,
            "sources_used": list(sources_used),
            "average_price_pcm": None,
            "median_price_pcm": None,
            "min_price_pcm": None,
            "max_price_pcm": None,
            "average_bedrooms": None,
            "bedroom_distribution": {},
            "property_type_distribution": {},
            "postcode_distribution_top": [],
            "furnished_distribution": {},
            "listings_with_images": 0,
            "listings_with_postcode": 0,
            "listings_with_coordinates": 0,
        }
        return {
            "success": True,
            "message": "No listings in sample for this query.",
            "location": combined.get("location"),
            "query": {
                "location": location,
                "area": area,
                "postcode": postcode,
                "min_price": min_price,
                "max_price": max_price,
                "min_bedrooms": min_bedrooms,
                "max_bedrooms": max_bedrooms,
                "limit": limit,
                "sort_by": sort_by,
            },
            "combined_errors": errors,
            "total_before_dedupe": combined.get("total_before_dedupe"),
            "total_after_dedupe": combined.get("total_after_dedupe"),
            "stats": empty_stats,
            "price_bands": analyze_price_bands([]),
            "bedroom_price_map": {},
            "value_candidates": [],
            "overall_analysis": {
                "market_price_level": "medium",
                "supply_level": "low",
                "bedroom_focus": None,
                "value_message": "No data to summarize.",
            },
            "listings": [],
        }

    stats = _build_basic_stats(listings, sources_used)
    price_bands = analyze_price_bands(listings)
    bed_map = analyze_bedroom_price_map(listings)
    value_c = analyze_value_candidates(listings, top_n=5)
    overall = _overall_analysis(stats, stats.get("bedroom_distribution") or {}, price_bands)

    listings_out = [_clean_listing_for_json(x) for x in listings]

    return {
        "success": bool(combined.get("success", True)),
        "message": "OK",
        "location": combined.get("location"),
        "query": {
            "location": location,
            "area": area,
            "postcode": postcode,
            "min_price": min_price,
            "max_price": max_price,
            "min_bedrooms": min_bedrooms,
            "max_bedrooms": max_bedrooms,
            "limit": limit,
            "sort_by": sort_by,
        },
        "combined_errors": errors,
        "total_before_dedupe": combined.get("total_before_dedupe"),
        "total_after_dedupe": combined.get("total_after_dedupe"),
        "stats": stats,
        "price_bands": price_bands,
        "bedroom_price_map": bed_map,
        "value_candidates": value_c,
        "overall_analysis": overall,
        "listings": listings_out,
    }


build_market_insight = get_market_insight


__all__ = [
    "analyze_bedroom_price_map",
    "analyze_price_bands",
    "analyze_value_candidates",
    "build_market_insight",
    "get_market_insight",
]
