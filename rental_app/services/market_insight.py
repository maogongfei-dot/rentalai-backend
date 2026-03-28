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
            "source_listing_id": L.get("source_listing_id"),
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


def build_market_summary(insight_result: dict[str, Any]) -> dict[str, Any]:
    """
    将 ``get_market_insight`` 返回转成人读摘要（规则驱动，无 LLM）。
    """
    stats = insight_result.get("stats") or {}
    price_bands = insight_result.get("price_bands") or {}
    overall = insight_result.get("overall_analysis") or {}
    value_c = insight_result.get("value_candidates") or []
    loc = (insight_result.get("location") or "").strip() or "this search area"

    n = int(stats.get("total_listings") or 0)
    avg = _to_float(stats.get("average_price_pcm"))
    med = _to_float(stats.get("median_price_pcm"))
    bd = stats.get("bedroom_distribution") or {}
    dom_band = price_bands.get("dominant_price_band")
    m_level = str(overall.get("market_price_level") or "medium")
    supply = str(overall.get("supply_level") or "low")
    focus = overall.get("bedroom_focus")
    with_pc = int(stats.get("listings_with_postcode") or 0)

    key_findings: list[str] = []
    risk_flags: list[str] = []

    if n == 0:
        return {
            "summary_title": f"Market snapshot: {loc}",
            "key_findings": ["No listings matched the current filters; widen location or budget."],
            "price_summary": "No price data.",
            "bedroom_summary": "No bedroom mix data.",
            "supply_summary": "No supply sample.",
            "value_summary": "No value candidates.",
            "recommendation": "Relax price or area constraints, or retry later.",
            "risk_flags": ["empty_sample"],
            "next_step_suggestion": "Expand search radius, increase max price, or remove bedroom filters.",
        }

    # 价格偏高
    if m_level == "high" or (avg is not None and avg >= 1700):
        key_findings.append("Rents in this sample skew high versus typical UK shared-london bands.")
        risk_flags.append("high_market_pcm")
    elif m_level == "low":
        key_findings.append("Observed pcm levels are relatively affordable in this sample.")

    # 样本量
    if n < 5:
        key_findings.append("Very few listings — treat numbers as indicative only.")
        risk_flags.append("small_sample")
    elif n < 15:
        key_findings.append("Modest sample size; conclusions are directional.")

    # 主流卧室
    if bd and focus is not None:
        cnt = bd.get(str(focus), 0)
        pct = round(100.0 * cnt / n, 1) if n else 0.0
        key_findings.append(f"The most common bedroom count is {focus} ({pct}% of sample).")

    # 性价比
    if value_c:
        key_findings.append(
            "Some listings sit below the sample average pcm — worth shortlisting for value."
        )

    # 邮编缺失
    if n > 0:
        miss_pc = n - with_pc
        miss_rate = miss_pc / n
        if miss_rate > 0.35:
            key_findings.append("A notable share of rows lack postcodes — address-level comparisons may be weaker.")
            risk_flags.append("postcode_data_gaps")

    price_summary = (
        f"Average pcm ~{avg if avg is not None else 'n/a'}, median ~{med if med is not None else 'n/a'}; "
        f"dominant band: {dom_band or 'n/a'}."
    )
    bedroom_summary = (
        f"Bedroom mix: {bd if bd else 'n/a'}; typical focus: {focus or 'n/a'}."
    )
    supply_summary = (
        f"{n} listings after merge/dedupe; supply level ({supply}) from sample size rules."
    )
    value_summary = (
        f"{len(value_c)} below-average pcm candidates flagged for review."
        if value_c
        else "No below-average pcm candidates under current rules."
    )

    rec_parts = [
        "Use median pcm as a budget anchor.",
        "Cross-check any favourite on the agency site before committing.",
    ]
    if value_c:
        rec_parts.insert(0, "Prioritise reviewing value-flagged listings that sit below the sample mean.")
    if n < 10:
        rec_parts.append("Broaden area or loosen filters to stabilise statistics.")

    next_step = "Compare top picks on commute and bills; verify deposit and contract terms independently."
    if n < 5:
        next_step = "Widen search (adjacent postcodes or higher budget) to build a stronger market picture first."

    return {
        "summary_title": f"Market snapshot: {loc}",
        "key_findings": key_findings or ["Sample processed; see stats for detail."],
        "price_summary": price_summary,
        "bedroom_summary": bedroom_summary,
        "supply_summary": supply_summary,
        "value_summary": value_summary,
        "recommendation": " ".join(rec_parts),
        "risk_flags": risk_flags,
        "next_step_suggestion": next_step,
    }


def build_market_commentary(insight_result: dict[str, Any]) -> dict[str, Any]:
    """别名，与 ``build_market_summary`` 相同。"""
    return build_market_summary(insight_result)


def build_market_decision_snapshot(insight_result: dict[str, Any]) -> dict[str, Any]:
    """
    短结论块，适合 Explain / UI 卡片（无 LLM）。
    """
    summ = build_market_summary(insight_result)
    stats = insight_result.get("stats") or {}
    value_c = insight_result.get("value_candidates") or []
    n = int(stats.get("total_listings") or 0)
    med = stats.get("median_price_pcm")
    overall = insight_result.get("overall_analysis") or {}

    if n == 0:
        return {
            "conclusion": "No listings to characterise this market slice.",
            "reasons": ["Filters or availability returned an empty set."],
            "warnings": summ.get("risk_flags") or [],
            "top_value_listing_ids": [],
            "top_value_listing_titles": [],
        }

    conclusion = (
        f"Median pcm around {med if med is not None else 'n/a'}; "
        f"{n} listings; market priced as {overall.get('market_price_level', 'medium')}."
    )

    reasons = [
        summ.get("supply_summary", ""),
        summ.get("price_summary", ""),
    ]
    reasons = [r for r in reasons if r]

    warnings = list(summ.get("risk_flags") or [])

    titles = [str(v.get("title") or "") for v in value_c if v.get("title")][:5]
    ids = []
    for v in value_c:
        sid = v.get("source_listing_id")
        if sid is not None and str(sid).strip():
            ids.append(str(sid).strip())
    ids = ids[:5]

    return {
        "conclusion": conclusion,
        "reasons": reasons,
        "warnings": warnings,
        "top_value_listing_ids": ids,
        "top_value_listing_titles": titles,
    }


def get_market_analysis_bundle(
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
    D7-4：一次返回 insight 全文 + 摘要 + decision_snapshot（供 API 使用）。
    """
    insight = get_market_insight(
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
    return {
        "success": bool(insight.get("success", True)),
        "location": insight.get("location"),
        "insight": insight,
        "summary": build_market_summary(insight),
        "decision_snapshot": build_market_decision_snapshot(insight),
    }


__all__ = [
    "analyze_bedroom_price_map",
    "analyze_price_bands",
    "analyze_value_candidates",
    "build_market_commentary",
    "build_market_decision_snapshot",
    "build_market_insight",
    "build_market_summary",
    "get_market_analysis_bundle",
    "get_market_insight",
]


def _cli_main() -> None:
    """调试：``python -m services.market_insight London`` — 打印 analysis bundle JSON。"""
    import json
    import sys

    loc = (sys.argv[1] if len(sys.argv) > 1 else "London").strip()
    bundle = get_market_analysis_bundle(location=loc, max_price=2500, limit=20, sort_by="price_asc")
    print(json.dumps(bundle, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    _cli_main()
