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


def _compute_star_rating(
    listing: dict[str, Any],
    market_insight: dict[str, Any],
    deal_score: float,
    decision: str,
    risk_level: str,
) -> float:
    """
    用户向星级：默认 3 星（普通房源），按相对均价与信息完整度加减分；步进 0.5；封顶 5 星。

    加分：月租低于样本均价 +1 星；完整度较高 +0.5 星。
    减分：月租高于样本均价 −1 星；完整度偏低 −0.5 星。

    一般不低于 2 星；仅当「特别差」（AVOID、或高风险、或 deal 分过低）时允许落到 1–2 星区间，避免满屏 1 星。
    """
    try:
        ds = float(deal_score)
    except (TypeError, ValueError):
        ds = 50.0
    ds = max(0.0, min(100.0, ds))

    d = str(decision or "").strip().upper()
    rl = str(risk_level or "low").lower()
    star = 3.0

    price = _to_float(listing.get("price_pcm"))
    stats = market_insight.get("stats") if isinstance(market_insight.get("stats"), dict) else {}
    avg = _to_float(stats.get("average_price_pcm"))
    if price is not None and price > 0 and avg is not None and avg > 0:
        if price < avg:
            star += 1.0
        elif price > avg:
            star -= 1.0

    calc = calculate_deal_score(listing, market_insight)
    sb = calc.get("score_breakdown") if isinstance(calc.get("score_breakdown"), dict) else {}
    cp = _to_float(sb.get("completeness"))
    if cp is not None:
        if cp >= 65.0:
            star += 0.5
        elif cp < 45.0:
            star -= 0.5

    star = min(5.0, star)

    star = round(star * 2.0) / 2.0

    especially_bad = d == "AVOID" or rl == "high" or ds < 40.0
    if star < 2.0:
        if especially_bad:
            star = max(1.0, star)
        else:
            star = 2.0

    return min(5.0, star)


def _star_reasons_zh(
    listing: dict[str, Any],
    market_insight: dict[str, Any],
    deal_score: float,
    risk_level: str,
    decision: str,
) -> list[str]:
    """1–3 条面向用户的中文理由（不写技术字段名）。"""
    reasons: list[str] = []
    price = _to_float(listing.get("price_pcm"))
    stats = market_insight.get("stats") if isinstance(market_insight.get("stats"), dict) else {}
    avg = _to_float(stats.get("average_price_pcm"))

    if price is not None and price > 0 and avg is not None and avg > 0:
        diff_pct = (avg - price) / avg * 100.0
        if price < avg:
            reasons.append(f"月租比本批样本均价低约 {abs(diff_pct):.0f}%，对预算更友好。")
        elif price > avg:
            reasons.append(f"月租高于样本均价约 {abs(diff_pct):.0f}%，需要多对比是否值回票价。")
        else:
            reasons.append("月租落在样本均价附近，属于常见水平。")

    bk = _bed_key(listing)
    bmap = market_insight.get("bedroom_price_map") or {}
    row = bmap.get(bk) if bk is not None and isinstance(bmap, dict) else None
    if price is not None and price > 0 and isinstance(row, dict):
        bavg = _to_float(row.get("avg_price"))
        if bavg is not None and bavg > 0 and bk is not None:
            if price < bavg:
                reasons.append(f"在同卧室数（{bk} 间）里，租金低于该档平均水平。")
            elif price > bavg:
                reasons.append("在同卧室数里租金偏高，建议对照地段与屋内条件。")

    rl = str(risk_level or "low").lower()
    if rl == "high":
        reasons.append("价格或信息上存在需要警惕的信号，建议先在原站核实再投入时间。")
    elif rl == "medium":
        reasons.append("部分关键信息不够完整，更适合愿意多做一步核对的人。")
    elif len(reasons) < 2:
        reasons.append("信息完整度与风险信号整体相对可控。")

    dec = str(decision or "").strip().upper()
    if dec == "DO" and rl == "low" and len(reasons) < 3:
        reasons.append("在本次搜索里综合排序靠前，适合优先排进看房清单。")
    elif dec == "AVOID" and len(reasons) < 3:
        reasons.append("与当前搜索目标相比，匹配度偏低，更适合作为备选或跳过。")
    elif dec == "CAUTION" and len(reasons) < 3:
        reasons.append("整体尚可，但仍有几处需要你在实地或原站确认。")

    while len(reasons) < 1:
        reasons.append("已纳入本轮候选，可按星级理解「先看谁、后看谁」。")
    return reasons[:3]


def _one_line_suggestion_zh(star: float, decision: str) -> str:
    d = str(decision or "").strip().upper()
    if star >= 4.5:
        return "适合想优先安排看房、希望尽快缩小范围的人。"
    if star >= 4.0:
        return "适合希望兼顾性价比与稳妥性的用户。"
    if star >= 3.0:
        return "适合愿意多做对比、接受一定取舍的用户。"
    if d == "AVOID":
        return "除非你有特别需求，否则建议先看其他更匹配的候选。"
    return "不太建议作为首选，除非你非常看重它的某一两个点。"


def _safety_env_proxy_score(listing: dict[str, Any], risk_level: str) -> float:
    """无外部治安数据：用信息完整度 + 规则风险近似「更稳妥」。"""
    rl = str(risk_level or "low").lower()
    pts = 0.0
    if (listing.get("postcode") or "").strip():
        pts += 28.0
    if (listing.get("image_url") or "").strip():
        pts += 28.0
    lat, lng = _to_float(listing.get("latitude")), _to_float(listing.get("longitude"))
    if lat is not None and lng is not None:
        pts += 22.0
    if (listing.get("address") or "").strip():
        pts += 12.0
    if (listing.get("listing_url") or "").strip():
        pts += 10.0
    if rl == "low":
        pts += 35.0
    elif rl == "medium":
        pts += 15.0
    else:
        pts -= 25.0
    return pts


def _value_score_for_listing(row: dict[str, Any], market_insight: dict[str, Any]) -> float:
    """租价相对更「划算」的近似分（0–100），用于综合推荐，不在文案里出现。"""
    calc = calculate_deal_score(row, market_insight)
    sb = calc.get("score_breakdown") if isinstance(calc.get("score_breakdown"), dict) else {}
    pv = _to_float(sb.get("price_vs_market"))
    bv = _to_float(sb.get("bedroom_value"))
    if pv is None:
        pv = 50.0
    if bv is None:
        bv = 50.0
    return (pv + bv) / 2.0


def build_star_final_verdict(
    items: list[dict[str, Any]],
    ranked_rows: list[dict[str, Any]],
    market_insight: dict[str, Any],
    location_label: str,
) -> dict[str, Any]:
    """
    综合结论（用户向）：最推荐（星 + 划算）、价格最优、更稳妥、总体建议。
    ``items`` 与 ``ranked_rows`` 顺序一致。
    """
    loc = (location_label or "").strip() or "这一带"
    empty: dict[str, Any] = {
        "best_overall": None,
        "best_for_price": None,
        "best_for_environment_safety": None,
        "overall_advice": f"这次还没筛出合适的几套，可以换个区域或把预算、卧室数稍微放宽一点，再搜一次「{loc}」。",
    }
    if not items or not ranked_rows:
        return empty

    n = min(len(items), len(ranked_rows))

    def _line_price(it: dict[str, Any]) -> str:
        t = _str(it.get("title")) or "这一套"
        return f"如果眼下最在意月租数字，「{t}」在这几套里更省一点，适合先拿来当比价的起点。"

    def _line_safety(it: dict[str, Any]) -> str:
        t = _str(it.get("title")) or "这一套"
        return (
            f"如果想心里更踏实一点，「{t}」的资料更齐、看起来也更让人放心，可以先从这里看起。"
        )

    def _line_best_overall(it: dict[str, Any]) -> str:
        t = _str(it.get("title")) or "这一套"
        return (
            f"综合来看，「{t}」星数高、租价也相对划算；如果你只能先深入一套，我会把它放在第一位。"
        )

    # 最推荐：星级 + 性价比（内部 value 分）综合最高
    composite: list[tuple[float, int]] = []
    for i in range(n):
        star = float(items[i].get("star_rating") or 0)
        vs = _value_score_for_listing(ranked_rows[i], market_insight)
        comp = star * 22.0 + vs * 0.82
        composite.append((comp, i))
    oi = max(composite, key=lambda x: x[0])[1]
    best_overall = {
        "title": _str(items[oi].get("title")) or "—",
        "line": _line_best_overall(items[oi]),
    }

    price_idx = 0
    best_p = None
    for i in range(n):
        p = _to_float(ranked_rows[i].get("price_pcm"))
        if p is not None and p > 0:
            if best_p is None or p < best_p:
                best_p = p
                price_idx = i
    if best_p is None:
        best_for_price = {"title": _str(items[0].get("title")) or "—", "line": _line_price(items[0])}
    else:
        best_for_price = {
            "title": _str(items[price_idx].get("title")) or "—",
            "line": _line_price(items[price_idx]),
        }

    safety_scores: list[tuple[float, int]] = []
    for i in range(n):
        row = ranked_rows[i]
        rk = analyze_listing_risks(row, market_insight)
        rl = str(rk.get("risk_level") or "low")
        sc = _safety_env_proxy_score(row, rl)
        safety_scores.append((sc, i))
    si = max(safety_scores, key=lambda x: x[0])[1]
    best_for_environment_safety = {
        "title": _str(items[si].get("title")) or "—",
        "line": _line_safety(items[si]),
    }

    stats = market_insight.get("stats") if isinstance(market_insight.get("stats"), dict) else {}
    try:
        n_total = int(stats.get("total_listings") or 0)
    except (TypeError, ValueError):
        n_total = 0

    stars = [float(x.get("star_rating") or 0) for x in items[:n]]
    avg_star = sum(stars) / len(stars) if stars else 0.0
    if n_total < 5:
        overall_advice = (
            f"这次在「{loc}」能挑的还不多，不必急着做决定。"
            "可以先按上面几套约着看一看；还想多比较的话，把条件稍微放宽一点再搜一轮也行。"
        )
    elif avg_star >= 3.5:
        overall_advice = (
            f"这次在「{loc}」看到的结果整体还不错，值得继续往下看。"
            "先挑一两套最顺眼的实地感受，再决定要不要一直盯这个区域和这个预算。"
        )
    elif avg_star >= 2.5:
        overall_advice = (
            f"这次在「{loc}」有几套还行，但也有需要取舍的地方。"
            "建议先看一两套再想想：还要不要继续在这个预算里找，或者稍微调整期望。"
        )
    else:
        overall_advice = (
            f"这次在「{loc}」筛出来的几套整体一般。如果时间不紧，可以微调区域或预算再搜；"
            "如果着急入住，就挑相对最顺眼的先落实，别硬扛不合适的。"
        )

    return {
        "best_overall": best_overall,
        "best_for_price": best_for_price,
        "best_for_environment_safety": best_for_environment_safety,
        "overall_advice": overall_advice,
    }


def _compose_market_snapshot_zh(
    loc: str,
    n_total: int,
    top_n: int,
    overall_en: str,
) -> str:
    """一页话市场印象（中文、非技术）。"""
    loc_s = loc or "本区域"
    if top_n == 0:
        return (
            f"在「{loc_s}」这次搜索里，暂时没有出现适合重点展开的候选。"
            "可以尝试放宽一点区域、预算或卧室数，再搜一次。"
        )
    head = f"在「{loc_s}」附近，本次样本里大约有 {n_total} 套房源参与比较；下面列出的是其中更值得先看的 {top_n} 套。"
    tail = "你可以把星级理解成「在当前搜索条件下，有多值得优先排进看房清单」，不必把它当成绝对打分。"
    if "high" in overall_en.lower() or "risk" in overall_en.lower():
        return head + " 需要提醒的是：前几名里仍有个别信息需要你在原站核实，先看星级高的，再决定要不要深入。" + tail
    if "small" in overall_en.lower() or "widen" in overall_en.lower():
        return head + " 由于整体样本不算大，建议把结论当成阶段性参考，条件允许时再多搜几次放大选择面。" + tail
    if "strong" in overall_en.lower() or "good" in overall_en.lower():
        return head + " 整体观感还不错，可以按星级从高到低安排时间，把最匹配的几套先看完。" + tail
    return head + " 建议先锁定星级更高的 1–2 套，再决定要不要继续盯这个区域和预算。" + tail


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

    star_rating = _compute_star_rating(listing, market_insight, deal_score, decision, risk_level)
    star_reasons = _star_reasons_zh(listing, market_insight, deal_score, risk_level, decision)
    one_line_suggestion = _one_line_suggestion_zh(star_rating, decision)

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
        "star_rating": star_rating,
        "star_reasons": star_reasons,
        "one_line_suggestion": one_line_suggestion,
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

        br = listing.get("bedrooms")
        try:
            bed_display = int(br) if br is not None and float(br) == int(float(br)) else br
        except (TypeError, ValueError):
            bed_display = br
        item: dict[str, Any] = {
            "title": ex.get("title") or _str(listing.get("title")) or "Listing",
            "address": listing.get("address"),
            "price_pcm": listing.get("price_pcm"),
            "bedrooms": bed_display,
            "image_url": listing.get("image_url"),
            "listing_url": listing.get("listing_url"),
            "star_rating": ex.get("star_rating"),
            "star_reasons": ex.get("star_reasons") or [],
            "one_line_suggestion": ex.get("one_line_suggestion") or "",
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
            "market_snapshot_zh": _compose_market_snapshot_zh(loc, n_total, 0, orec),
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
        "market_snapshot_zh": _compose_market_snapshot_zh(loc, n_total, top_n, overall_recommendation),
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
    report["star_final_verdict"] = build_star_final_verdict(
        explanations.get("items") or [],
        ranked.get("top_deals") or [],
        insight,
        str(loc_key or ""),
    )

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
    "build_star_final_verdict",
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
