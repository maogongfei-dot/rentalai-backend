"""
Phase D9：Explain / Recommendation Output Engine —— 规则版解释文案，复用 D7/D8 结果。
"""

from __future__ import annotations

import copy
from typing import Any

from services.deal_engine import (
    analyze_listing_risks,
    build_deal_decision,
    calculate_deal_score,
    deal_tag_from_score,
    rank_deals,
)


def _to_float(v: Any) -> float | None:
    if v is None or isinstance(v, bool):
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _bed_key(listing: dict[str, Any]) -> str | None:
    b = listing.get("bedrooms")
    if b is None:
        return None
    try:
        x = float(b)
        if x < 0:
            return None
        if x == 0:
            return "0"
        return str(int(x)) if x == int(x) else str(round(x, 1))
    except (TypeError, ValueError):
        return None


def _str(v: Any) -> str:
    if v is None:
        return ""
    return str(v).strip()


def _price_bedroom_narrative(
    listing: dict[str, Any],
    market_insight: dict[str, Any],
    why_rec: list[str],
    why_not: list[str],
) -> tuple[str, str]:
    """price_position / bedroom_position 文案 + 填充 why 列表。"""
    price = _to_float(listing.get("price_pcm"))
    stats = market_insight.get("stats") if isinstance(market_insight.get("stats"), dict) else {}
    avg = _to_float(stats.get("average_price_pcm"))

    price_position = "Insufficient data to compare to the market average."
    if price is not None and price > 0 and avg is not None and avg > 0:
        diff_pct = (avg - price) / avg * 100.0
        if price < avg:
            price_position = f"Below sample average pcm (~{diff_pct:.0f}% cheaper)."
            why_rec.append(
                f"Monthly rent is below the sample average (~{abs(diff_pct):.0f}% vs average)."
            )
        elif price > avg:
            price_position = f"Above sample average pcm (~{abs(diff_pct):.0f}% more expensive)."
            why_not.append(
                f"Monthly rent is above the sample average (~{abs(diff_pct):.0f}% vs average)."
            )
        else:
            price_position = "In line with the sample average pcm."

    bk = _bed_key(listing)
    bmap = market_insight.get("bedroom_price_map") or {}
    row = bmap.get(bk) if bk is not None and isinstance(bmap, dict) else None
    bedroom_position = "No segment average for this bedroom count (or bedrooms unknown)."
    if price is not None and price > 0 and isinstance(row, dict):
        bavg = _to_float(row.get("avg_price"))
        if bavg is not None and bavg > 0 and bk is not None:
            diff_b = (bavg - price) / bavg * 100.0
            if price < bavg:
                bedroom_position = f"Below the {bk}-bed segment average in this sample."
                why_rec.append(
                    f"Cheaper than other {bk}-bed listings in this sample (~{abs(diff_b):.0f}% vs segment avg)."
                )
            elif price > bavg:
                bedroom_position = f"Above the {bk}-bed segment average in this sample."
                why_not.append(
                    f"Pricier than other {bk}-bed listings in this sample (~{abs(diff_b):.0f}% vs segment avg)."
                )
            else:
                bedroom_position = f"In line with the {bk}-bed segment average."

    return price_position, bedroom_position


def _data_quality_line(listing: dict[str, Any], score_breakdown: dict[str, Any]) -> str:
    cp = _to_float(score_breakdown.get("completeness"))
    parts: list[str] = []
    if (listing.get("postcode") or "").strip():
        parts.append("postcode present")
    else:
        parts.append("postcode missing")
    if (listing.get("image_url") or "").strip():
        parts.append("image present")
    else:
        parts.append("no image")
    if (listing.get("listing_url") or "").strip():
        parts.append("listing URL present")
    else:
        parts.append("listing URL missing")
    if _bed_key(listing) is not None:
        parts.append("bedrooms known")
    else:
        parts.append("bedrooms missing")
    tail = f" (completeness score {cp:.0f}/100)." if cp is not None else "."
    return "; ".join(parts) + tail


def _missing_field_notes(listing: dict[str, Any], why_not: list[str]) -> None:
    if not (listing.get("postcode") or "").strip():
        why_not.append("Postcode missing — harder to verify area and commute.")
    if not (listing.get("image_url") or "").strip():
        why_not.append("No property image — review carefully on the portal.")
    if not (listing.get("listing_url") or "").strip():
        why_not.append("No listing URL — open the advert on the original site before deciding.")
    if _bed_key(listing) is None:
        why_not.append("Bedroom count missing — compare against similar-sized listings with care.")


def _headline(decision: str, deal_tag: str, deal_score: float, risk_level: str, risk_flags: list[str]) -> str:
    bits = [f"{decision}: {deal_tag} deal (score {deal_score:.0f})."]
    if risk_level == "high":
        bits.append("High listing risk.")
    elif risk_level == "medium":
        bits.append("Some data gaps or weak fields.")
    else:
        bits.append("Low rule-based listing risk.")
    if risk_flags:
        bits.append(f"Flags: {', '.join(risk_flags[:4])}" + ("…" if len(risk_flags) > 4 else "") + ".")
    return " ".join(bits)


def _action_suggestions_trim(suggestions: list[str], decision: str) -> list[str]:
    """保证 2–4 条英文 actionable 句子。"""
    base = [s for s in suggestions if isinstance(s, str) and s.strip()]
    extra: list[str] = [
        "Compare with similar listings for the same bedroom count in this search area.",
        "Verify postcode and transport links on a map before viewing.",
        "Request bills, deposit, and contract terms from the agent or landlord.",
        "Review listing images and floorplan (if any) on the live portal.",
    ]
    for e in extra:
        if len(base) >= 4:
            break
        if e not in base:
            base.append(e)
    if decision == "AVOID":
        avoid_extra = "Do not proceed until you have a verifiable source link and plausible price."
        if avoid_extra not in base:
            base.append(avoid_extra)
    while len(base) < 2:
        for e in extra:
            if e not in base:
                base.append(e)
                break
        else:
            base.append("Cross-check this listing on the original property portal.")
        if len(base) >= 2:
            break
    return base[:4]


def _uniq_str(xs: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for x in xs:
        if x and x not in seen:
            seen.add(x)
            out.append(x)
    return out


def build_listing_explanation(listing: dict[str, Any], market_insight: dict[str, Any]) -> dict[str, Any]:
    """
    单房源解释块：复用 D8 ``build_deal_decision``（内含 deal 分与风险），不重复评分逻辑。
    """
    if not isinstance(listing, dict):
        listing = {}
    if not isinstance(market_insight, dict):
        market_insight = {}

    dec = build_deal_decision(listing, market_insight)
    deal_score = float(dec.get("score") or 0.0)
    deal_tag = deal_tag_from_score(deal_score)

    decision = str(dec.get("decision") or "CAUTION")
    risk_flags = [str(x) for x in (dec.get("risk_flags") or []) if x is not None]
    risk_level = str(dec.get("risk_level") or "low")

    title = _str(listing.get("title")) or "Listing"

    why_rec: list[str] = []
    why_not: list[str] = []
    price_position, bedroom_position = _price_bedroom_narrative(
        listing, market_insight, why_rec, why_not
    )
    _missing_field_notes(listing, why_not)
    why_rec = _uniq_str(why_rec)
    why_not = _uniq_str(why_not)

    sb = dec.get("score_breakdown") if isinstance(dec.get("score_breakdown"), dict) else {}
    data_quality = _data_quality_line(listing, sb)

    headline = _headline(decision, deal_tag, deal_score, risk_level, risk_flags)

    actions = _action_suggestions_trim(list(dec.get("action_suggestion") or []), decision)

    out: dict[str, Any] = {
        "title": title,
        "deal_score": round(deal_score, 2),
        "deal_tag": deal_tag,
        "decision": decision,
        "headline": headline,
        "why_recommended": why_rec,
        "why_not_recommended": why_not,
        "risk_flags": risk_flags,
        "price_position": price_position,
        "bedroom_position": bedroom_position,
        "data_quality": data_quality,
        "action_suggestion": actions,
    }
    return out


def build_top_deals_explanations(
    listings: list[dict[str, Any]],
    market_insight: dict[str, Any],
    top_n: int = 10,
    *,
    ranked_deals: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    先 ``rank_deals`` 取 Top N（或复用已算好的 ``ranked_deals``），再对每条生成解释。

    传入 ``ranked_deals`` 时可避免重复排序（API 批量流程推荐）。
    """
    if not isinstance(listings, list):
        listings = []
    if not isinstance(market_insight, dict):
        market_insight = {}

    try:
        n = max(1, int(top_n)) if top_n is not None else 10
    except (TypeError, ValueError):
        n = 10

    if ranked_deals is not None and isinstance(ranked_deals, dict):
        rows = list(ranked_deals.get("top_deals") or [])
    else:
        ranked = rank_deals(listings, market_insight, top_n=n)
        rows = ranked.get("top_deals") or []

    items: list[dict[str, Any]] = []
    for raw in rows:
        if not isinstance(raw, dict):
            continue
        listing = copy.deepcopy(raw)
        ex = build_listing_explanation(listing, market_insight)

        src = listing.get("source")

        item: dict[str, Any] = {
            "title": ex.get("title") or _str(listing.get("title")) or "Listing",
            "address": listing.get("address"),
            "price_pcm": listing.get("price_pcm"),
            "bedrooms": listing.get("bedrooms"),
            "source": src,
            "listing_url": listing.get("listing_url"),
            "deal_score": ex.get("deal_score"),
            "deal_tag": ex.get("deal_tag"),
            "decision": ex.get("decision"),
            "headline": ex.get("headline"),
        }
        items.append(item)

    return {"count": len(items), "items": items}


def build_market_recommendation_report(
    location: str | None,
    market_insight: dict[str, Any],
    ranked_deals: dict[str, Any],
) -> dict[str, Any]:
    """
    市场 + Top deals 综合建议（规则生成）。``ranked_deals`` 为 ``rank_deals`` 的返回 dict。
    """
    if not isinstance(market_insight, dict):
        market_insight = {}
    if not isinstance(ranked_deals, dict):
        ranked_deals = {}

    loc = _str(location) if location is not None else ""
    if not loc:
        loc = _str(market_insight.get("location")) or "this search area"

    overall = market_insight.get("overall_analysis") if isinstance(market_insight.get("overall_analysis"), dict) else {}
    m_level = str(overall.get("market_price_level") or "medium")
    supply = str(overall.get("supply_level") or "low")
    focus = overall.get("bedroom_focus")
    focus_s = str(focus) if focus is not None else "mixed sizes"

    market_positioning = (
        f"In this sample, rents look **{m_level}** versus typical bands, supply is **{supply}**, "
        f"and the most common bedroom count is **{focus_s}**."
    ).replace("**", "")

    stats = market_insight.get("stats") if isinstance(market_insight.get("stats"), dict) else {}
    try:
        n_total = int(stats.get("total_listings") or 0)
    except (TypeError, ValueError):
        n_total = 0

    top_deals = [x for x in (ranked_deals.get("top_deals") or []) if isinstance(x, dict)]
    top_n = len(top_deals)

    buyer_strategy: list[str] = [
        "Sort by deal score, then filter to listings with postcode + URL for faster vetting.",
        "Prefer same-bedroom comparisons within this postcode cluster or transport corridor.",
        "Treat very high scores with missing URLs as “research only” until verified.",
        "Book viewings only after price and address check out on the live listing.",
    ]

    if top_n == 0:
        wtn = [
            "Broaden search filters to increase the sample before relying on rankings.",
            "Retry with a wider area, higher limit, or relaxed price/bed constraints.",
            "Confirm property portals return data for this location.",
        ]
        if n_total >= 5:
            wtn.append("If listings exist but none rank, check for missing prices or broken merges.")
        orec = (
            "No listings in sample — widen the area, relax price/bed filters, or retry later before deciding."
            if n_total == 0
            else "Sample exists but no top deals to highlight — refine filters or increase limit."
        )
        bo = ["No top deals to compare yet — expand search to surface candidates."]
        mr = ["Insufficient data in the top slice to summarise common risk patterns."]
        summ = f"{loc}: inconclusive yet - expand search criteria before committing time to viewings."
        return {
            "location": loc,
            "market_positioning": market_positioning,
            "overall_recommendation": orec,
            "best_opportunities": bo,
            "main_risks": mr,
            "what_to_do_next": wtn[:5],
            "buyer_strategy": buyer_strategy[:6],
            "summary_sentence": summ,
            "readable_sections": {
                "market_situation": market_positioning,
                "worth_continuing": orec,
                "top_opportunities": bo,
                "main_risks": mr,
                "next_steps": wtn[:5],
            },
        }

    tags = [str(x.get("deal_tag") or "") for x in top_deals]
    excellent_good = sum(1 for t in tags if t in ("excellent", "good"))

    high_risk_n = 0
    flag_counts: dict[str, int] = {}
    below_avg_n = 0
    below_seg_n = 0
    completeness_vals: list[float] = []

    avg_pcm = _to_float(stats.get("average_price_pcm"))
    bmap = market_insight.get("bedroom_price_map") or {}

    for row in top_deals:
        rk = analyze_listing_risks(row, market_insight)
        if str(rk.get("risk_level") or "") == "high":
            high_risk_n += 1
        for f in rk.get("risk_flags") or []:
            fc = str(f)
            flag_counts[fc] = flag_counts.get(fc, 0) + 1

        price = _to_float(row.get("price_pcm"))
        if price is not None and price > 0 and avg_pcm is not None and avg_pcm > 0 and price < avg_pcm:
            below_avg_n += 1

        bk = _bed_key(row)
        br = bmap.get(bk) if bk is not None and isinstance(bmap, dict) else None
        if isinstance(br, dict):
            bavg = _to_float(br.get("avg_price"))
            if price is not None and price > 0 and bavg is not None and bavg > 0 and price < bavg:
                below_seg_n += 1

        cs = calculate_deal_score(row, market_insight)
        sb = cs.get("score_breakdown") if isinstance(cs.get("score_breakdown"), dict) else {}
        cpl = _to_float(sb.get("completeness"))
        if cpl is not None:
            completeness_vals.append(cpl)

    # overall_recommendation
    if n_total < 5:
        overall_recommendation = (
            "Sample is very small — widen the area, relax price/bed filters, or retry later before deciding."
        )
    elif high_risk_n >= max(1, top_n // 2):
        overall_recommendation = (
            "Several top-ranked rows still carry high listing risk — proceed with caution and verify sources."
        )
    elif excellent_good >= max(2, (top_n + 1) // 2):
        overall_recommendation = (
            "Several strong or good-value candidates appear — shortlist and follow up on the best matches."
        )
    else:
        overall_recommendation = (
            "Mixed quality in the top slice — keep comparing and prioritise rows with complete data and sane prices."
        )

    best_opportunities: list[str] = []
    if below_avg_n >= max(1, top_n // 3):
        best_opportunities.append("Multiple top deals sit below the sample average pcm — value may be available.")
    if below_seg_n >= max(1, top_n // 3):
        best_opportunities.append("Some top deals beat their bedroom-segment average — stronger bedroom-to-price value.")
    if completeness_vals and sum(completeness_vals) / len(completeness_vals) >= 70:
        best_opportunities.append("Top rows tend to have richer listing details (images, location fields) for comparison.")
    if not best_opportunities:
        best_opportunities.append("Review top scores case-by-case; patterns will emerge as the sample grows.")

    main_risks: list[str] = []
    risk_labels = {
        "price_suspiciously_low": "Unusually low price vs the sample (verify against scams).",
        "listing_url_missing": "Missing listing URL — hard to open the original advert.",
        "missing_location_identity": "Missing address/postcode on some rows — weaker location verification.",
        "no_image": "Missing property images on some rows.",
        "bedrooms_missing": "Missing bedroom count on some rows.",
    }
    for code, label in risk_labels.items():
        if flag_counts.get(code, 0) > 0:
            main_risks.append(label)
    if not main_risks:
        main_risks.append("No dominant risk pattern in the top slice — still verify each listing on the portal.")

    what_to_do_next: list[str] = [
        "Save 3–5 favourites and compare pcm against the sample average and bedroom segment.",
        "Open each shortlist on the original portal to confirm photos, address, and availability.",
        "Map postcodes for commute and amenities before booking viewings.",
        "Ask agents for total move-in cost (deposit, fees) in writing.",
    ]
    if n_total < 10:
        what_to_do_next.insert(0, "Broaden search filters to increase the sample before relying on rankings.")

    if excellent_good >= 2 and high_risk_n < max(1, top_n // 2):
        summary_sentence = f"{loc}: worth continuing - enough promising leads in this sample to justify deeper shortlisting."
    elif n_total < 5:
        summary_sentence = f"{loc}: inconclusive yet - expand search criteria before committing time to viewings."
    elif high_risk_n >= max(1, top_n // 2):
        summary_sentence = f"{loc}: proceed carefully - many top rows need verification before viewings."
    else:
        summary_sentence = f"{loc}: moderately promising - compare a few shortlisted flats and validate on-portal details."

    return {
        "location": loc,
        "market_positioning": market_positioning,
        "overall_recommendation": overall_recommendation,
        "best_opportunities": best_opportunities[:6],
        "main_risks": main_risks[:8],
        "what_to_do_next": what_to_do_next[:5],
        "buyer_strategy": buyer_strategy[:6],
        "summary_sentence": summary_sentence,
        "readable_sections": {
            "market_situation": market_positioning,
            "worth_continuing": overall_recommendation,
            "top_opportunities": best_opportunities[:6],
            "main_risks": main_risks[:8],
            "next_steps": what_to_do_next[:5],
        },
    }


def build_market_explain_bundle(
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
    top_n: int = 10,
) -> dict[str, Any]:
    """
    D9-4：一次拉 insight → rank → explanations → recommendation report（供 API / CLI）。
    """
    from services.market_insight import build_market_summary, get_market_insight

    try:
        tn = max(1, int(top_n)) if top_n is not None else 10
    except (TypeError, ValueError):
        tn = 10

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
    listings = insight.get("listings") or []
    ranked = rank_deals(listings, insight, top_n=tn)
    explanations = build_top_deals_explanations(
        listings,
        insight,
        top_n=tn,
        ranked_deals=ranked,
    )
    loc_key = location or area or postcode or insight.get("location")
    report = build_market_recommendation_report(loc_key, insight, ranked)

    return {
        "success": bool(insight.get("success", True)),
        "location": insight.get("location"),
        "query": insight.get("query"),
        "market_summary": build_market_summary(insight),
        "top_deals": ranked,
        "explanations": explanations,
        "recommendation_report": report,
    }


__all__ = [
    "build_listing_explanation",
    "build_market_explain_bundle",
    "build_market_recommendation_report",
    "build_top_deals_explanations",
]


def _cli_main() -> None:
    """调试：``python -m services.explain_engine London`` — 打印 recommendation_report（需可访问房源源）。"""
    import json
    import sys

    loc = (sys.argv[1] if len(sys.argv) > 1 else "London").strip()
    bundle = build_market_explain_bundle(location=loc or None, limit=15, top_n=5)
    rep = bundle.get("recommendation_report") or {}
    print(json.dumps(rep, indent=2, ensure_ascii=False, default=str))
    print("--- summary_sentence ---")
    print(rep.get("summary_sentence", ""))


if __name__ == "__main__":
    _cli_main()
