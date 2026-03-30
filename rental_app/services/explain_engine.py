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


def _overall_stance_zh(decision: str, risk_level: str) -> str:
    """面向用户的总体结论：推荐 / 不推荐 / 谨慎选择（不涉及公式或字段名）。"""
    d = str(decision or "").strip().upper()
    rl = str(risk_level or "low").lower()
    if d == "AVOID":
        return "不推荐"
    if rl == "high":
        return "谨慎选择"
    if d == "DO":
        return "推荐"
    return "谨慎选择"


def _en_reason_line_to_zh(line: str) -> str | None:
    """把英文 why 行压成一条口语中文（仅展示层）。"""
    s = (line or "").strip()
    if not s:
        return None
    low = s.lower()
    if "below the sample average" in low or "below the sample" in low:
        return "租金比这次搜到的均价更便宜一些。"
    if "above the sample average" in low or "above the sample" in low:
        return "租金比这次搜到的均价更高一些。"
    if "cheaper than other" in low and "bed" in low:
        return "和同卧室数的房源比，这套租金更划算。"
    if "pricier than other" in low and "bed" in low:
        return "和同卧室数的房源比，这套偏贵。"
    if "postcode" in low and "missing" in low:
        return "邮编缺失，地段和通勤要自己在原站多核对。"
    if "no property image" in low or "no image" in low:
        return "缺少实拍图，点进原站看清楚再决定。"
    if "no listing url" in low or ("listing url" in low and "missing" in low):
        return "缺少原广告链接，务必在平台上找到同一套再聊。"
    if "bedroom count missing" in low or "bedrooms missing" in low:
        return "卧室数量没写清，对比时要特别留意面积和房型。"
    return None


def _pick_plain_reasons_zh(ex: dict[str, Any], max_n: int = 5) -> list[str]:
    """3–5 条人话理由：优先已有中文 star_reasons，再补英文 why 的口语翻译。"""
    min_n, cap = 3, max(3, min(max_n, 5))
    star_reasons = [str(x).strip() for x in (ex.get("star_reasons") or []) if str(x).strip()]
    why_rec = [str(x).strip() for x in (ex.get("why_recommended") or []) if str(x).strip()]
    out: list[str] = []
    for x in star_reasons:
        if x and x not in out:
            out.append(x)
        if len(out) >= cap:
            return out[:cap]
    for line in why_rec:
        zh = _en_reason_line_to_zh(line)
        if zh and zh not in out:
            out.append(zh)
        if len(out) >= cap:
            break
    one_line = str(ex.get("one_line_suggestion") or "").strip()
    if one_line and one_line not in out and len(out) < cap:
        out.append(one_line)
    why_not = [str(x).strip() for x in (ex.get("why_not_recommended") or []) if str(x).strip()]
    for line in why_not:
        if len(out) >= cap:
            break
        zh = _en_reason_line_to_zh(line)
        if zh and zh not in out:
            out.append(zh)
    while len(out) < min_n:
        out.append("建议结合预算和通勤，把这套放进你的对比清单里再决定。")
        if len(out) >= min_n:
            break
    return out[:cap]


def _action_lines_zh_from_en(actions: list[str], decision: str) -> list[str]:
    """把规则引擎的英文建议翻成可执行的中文短句（展示层）。"""
    d = str(decision or "").strip().upper()
    lines: list[str] = []
    for raw in actions:
        if not isinstance(raw, str) or not raw.strip():
            continue
        low = raw.lower()
        if "shortlist" in low or "viewing" in low:
            lines.append("挑两三套合适的，优先预约实地看房。")
        elif "bills" in low or "deposit" in low or "portal" in low:
            lines.append("在原广告页核对租金、押金，并问清水电费是否包在房租里。")
        elif "address" in low or "postcode" in low or "photo" in low:
            lines.append("用地图核对地址和邮编，并对照原站上的照片。")
        elif "cross-check" in low or "price" in low:
            lines.append("和同区域、同卧室数的房源比一比价格是否合理。")
        elif "too good" in low or "suspicious" in low:
            lines.append("如果价格低得离谱，先当心上当，核实来源再往下走。")
        elif "verifiable" in low or "url" in low or "agent" in low:
            lines.append("找到可核对的广告链接或中介联系方式，再考虑下一步。")
        else:
            lines.append("按原广告信息逐步核实，再决定是否联系中介或房东。")
        if len(lines) >= 4:
            break
    base_extra = [
        "主动联系中介或房东，问清入住时间与能否议价。",
        "确认账单（bill）包哪些、不包哪些，避免入住后踩坑。",
    ]
    for b in base_extra:
        if len(lines) >= 4:
            break
        if b not in lines:
            lines.append(b)
    if d == "AVOID" and not any("上当" in x or "核实" in x for x in lines):
        lines.append("在信息补齐之前，先不要付定金或透露过多个人信息。")
    return lines[:4] if lines else ["先在房源网站上把地址、租金和照片核对一遍，再联系对方。"]


def _price_score_bucket_from_vs_market(pv: float | None) -> int | None:
    """把 D8 的 price_vs_market（0–100）映射为 1–5 档；档越低表示相对样本越不占优（偏贵）。"""
    if pv is None:
        return None
    try:
        x = float(pv)
    except (TypeError, ValueError):
        return None
    x = max(0.0, min(100.0, x))
    # [0,20)→1 … [80,100]→5；1–2 档对应「价格偏高」侧（约 pv<40）
    return max(1, min(5, int(x // 20) + 1))


def generate_followup_questions(result: dict[str, Any]) -> list[str]:
    """
    根据房源/检索上下文生成【下一步】引导提问（展示层，不参与评分）。

    ``result`` 约定字段（均可选）：
    - ``final_score``: 综合分，单套场景下与星级一致（约 1–5）
    - ``price_score``: 1–5，越低表示相对样本越偏贵
    - ``risk_flag``: 是否存在值得关注的风险信号
    - ``has_multiple_options``: 是否有多套可对比
    """
    questions: list[str] = []

    fs = _to_float(result.get("final_score"))
    if fs is None:
        fs = 0.0

    ps_raw = result.get("price_score")
    ps_val: float | None
    try:
        ps_val = float(ps_raw) if ps_raw is not None else None
    except (TypeError, ValueError):
        ps_val = None

    if fs >= 4:
        questions.append("是否需要我帮你生成联系中介的话术？")
        questions.append("是否需要我帮你确认这个房源的bill情况？")

    if ps_val is not None and ps_val <= 2:
        questions.append("是否需要我帮你判断这个价格是否可以砍价？")

    if result.get("risk_flag"):
        questions.append("是否需要我帮你检查这个房源的合同风险？")

    if result.get("has_multiple_options"):
        questions.append("是否需要我帮你对比其他房源？")

    out = _uniq_str([q for q in questions if isinstance(q, str) and q.strip()])
    if not out:
        out.append("是否需要我帮你继续筛选更合适的房源？")
    return out


def _followup_result_from_listing_ex(ex: dict[str, Any]) -> dict[str, Any]:
    """由 ``build_listing_explanation`` 产出块构造 ``generate_followup_questions`` 入参。"""
    fs = _to_float(ex.get("star_rating"))
    if fs is None:
        fs = 0.0
    sb = ex.get("score_breakdown") if isinstance(ex.get("score_breakdown"), dict) else {}
    pv = _to_float(sb.get("price_vs_market"))
    bucket = _price_score_bucket_from_vs_market(pv)
    price_score = float(bucket) if bucket is not None else 3.0

    rflags = ex.get("risk_flags") or []
    rl = str(ex.get("risk_level") or "low").lower()
    dec = str(ex.get("decision") or "").strip().upper()
    risk_flag = bool(rflags) or rl in ("high", "medium") or dec == "AVOID"

    return {
        "final_score": fs,
        "price_score": price_score,
        "risk_flag": risk_flag,
        "has_multiple_options": False,
    }


def _followup_result_for_market_bundle(
    *,
    items: list[dict[str, Any]],
    best_title: str,
    top_n: int,
    high_risk_n: int,
    ranked_deals: dict[str, Any] | None,
    market_insight: dict[str, Any] | None,
) -> dict[str, Any]:
    """多套结果：用「最佳房源」对应的星级与价格维度构造提问上下文。"""
    top_rows = list(ranked_deals.get("top_deals") or []) if isinstance(ranked_deals, dict) else []
    idx = 0
    bt = _str(best_title)
    for i, it in enumerate(items):
        if _str(it.get("title")) == bt:
            idx = i
            break
    fs = _to_float(items[idx].get("star_rating")) if idx < len(items) else None
    if fs is None:
        fs = 0.0

    price_score = 3.0
    if market_insight and idx < len(top_rows):
        calc = calculate_deal_score(top_rows[idx], market_insight)
        sb = calc.get("score_breakdown") if isinstance(calc.get("score_breakdown"), dict) else {}
        pv = _to_float(sb.get("price_vs_market"))
        b = _price_score_bucket_from_vs_market(pv)
        if b is not None:
            price_score = float(b)

    risk_flag = high_risk_n > 0

    return {
        "final_score": fs,
        "price_score": price_score,
        "risk_flag": risk_flag,
        "has_multiple_options": top_n >= 2,
    }


def _format_analysis_block_zh(
    *,
    conclusion_lines: list[str],
    reasons: list[str],
    suggestions: list[str],
    questions: list[str],
) -> str:
    """统一四段式排版（结论 / 原因 / 建议 / 下一步提问）。"""
    c_lines = [x.strip() for x in conclusion_lines if x and str(x).strip()]
    r_lines = [x.strip() for x in reasons if x and str(x).strip()]
    s_lines = [x.strip() for x in suggestions if x and str(x).strip()]
    q_lines = [x.strip() for x in questions if x and str(x).strip()]

    parts: list[str] = [
        "===== 🏠 租房分析结果 =====",
        "",
        "【结论】",
    ]
    parts.extend(c_lines)
    parts.extend(["", "【原因】"])
    for b in r_lines:
        parts.append(f"- {b}")
    parts.extend(["", "【建议】"])
    for b in s_lines:
        parts.append(f"- {b}")
    parts.extend(["", "【下一步】"])
    for q in q_lines:
        parts.append(f"👉 {q}")
    return "\n".join(parts).rstrip() + "\n"


def _choice_line_for_stance_zh(stance: str, title: str) -> str:
    t = title or "该房源"
    if stance == "不推荐":
        return f"不建议优先选择：「{t}」"
    if stance == "谨慎选择":
        return f"谨慎考虑：「{t}」"
    return f"建议选择：「{t}」"


def format_single_listing_analysis_zh(ex: dict[str, Any]) -> str:
    """单套房源：四段式展示（仅排版，不重新算分）。"""
    if not isinstance(ex, dict):
        ex = {}
    title = _str(ex.get("title")) or "该房源"
    decision = str(ex.get("decision") or "CAUTION")
    risk_level = str(ex.get("risk_level") or "low")
    stance = _overall_stance_zh(decision, risk_level)

    conclusion_lines = [
        f"总体：{stance}",
        _choice_line_for_stance_zh(stance, title),
    ]
    reasons = _pick_plain_reasons_zh(ex, 5)
    actions_en = list(ex.get("action_suggestion") or [])
    suggestions = _action_lines_zh_from_en(actions_en, decision)
    questions = generate_followup_questions(_followup_result_from_listing_ex(ex))
    return _format_analysis_block_zh(
        conclusion_lines=conclusion_lines,
        reasons=reasons,
        suggestions=suggestions,
        questions=questions,
    )


def _market_overall_stance_zh(
    top_n: int,
    high_risk_n: int,
    excellent_good: int,
    n_total: int,
) -> str:
    """市场级总体：推荐 / 不推荐 / 谨慎选择。"""
    if top_n <= 0:
        return "谨慎选择"
    if n_total < 3:
        return "谨慎选择"
    half = max(1, top_n // 2)
    if high_risk_n >= half:
        return "谨慎选择"
    if excellent_good >= max(2, (top_n + 1) // 2):
        return "推荐"
    if excellent_good == 0 and high_risk_n == 0:
        return "谨慎选择"
    return "谨慎选择"


def _en_bullet_to_zh_market(s: str) -> str:
    low = (s or "").lower()
    if "below the sample average" in low:
        return "前几名里有多套租金低于本次样本均价，可以多关注性价比。"
    if "bedroom-segment" in low or "segment average" in low:
        return "有的套在同卧室数里比均价更划算，适合放进短名单。"
    if "richer listing" in low or "details" in low:
        return "前几名信息相对完整，方便你在网上先做一轮筛选。"
    if "widen" in low or "broaden" in low or "expand" in low:
        return "先把搜索范围或条件放宽一点，多攒几条再比较。"
    if "scam" in low or "verify" in low and "price" in low:
        return "若租金低得不寻常，务必在原站核实，谨防虚假信息。"
    if "missing listing url" in low or "url" in low:
        return "部分条目缺少原广告链接，点进平台找到同一套再联系。"
    if "missing address" in low or "postcode" in low:
        return "有些地址信息不全，用地图和邮编自己多核对一遍。"
    if "no image" in low or "images" in low:
        return "有的房源没图，一定要打开原广告看图再决定。"
    if "bedroom count" in low:
        return "有的卧室数没写清，对比时留意面积和房型描述。"
    if "verify each" in low or "portal" in low:
        return "每一套都建议在原租房网站上再确认一遍细节。"
    return "结合预算和地段，把最顺眼的一两套先约出来实地看看。"


def compose_market_analysis_display_zh(
    *,
    location: str,
    report: dict[str, Any],
    explanations: dict[str, Any],
    star_final_verdict: dict[str, Any],
    ranked_deals: dict[str, Any] | None = None,
    market_insight: dict[str, Any] | None = None,
) -> str:
    """
    多套/市场级：四段式展示。依赖 ``build_market_recommendation_report`` 写入的 ``display_context``，
    以及 ``star_final_verdict``、``explanations``，不重复算分。
    """
    if not isinstance(report, dict):
        report = {}
    if not isinstance(explanations, dict):
        explanations = {}
    if not isinstance(star_final_verdict, dict):
        star_final_verdict = {}

    loc = (location or report.get("location") or "本区域").strip() or "本区域"
    items = [x for x in (explanations.get("items") or []) if isinstance(x, dict)]

    ctx = report.get("display_context") if isinstance(report.get("display_context"), dict) else {}
    try:
        top_n = int(ctx.get("top_n") if ctx.get("top_n") is not None else len(items))
    except (TypeError, ValueError):
        top_n = len(items)
    try:
        n_total = int(ctx.get("n_total") or 0)
    except (TypeError, ValueError):
        n_total = 0
    try:
        high_risk_n = int(ctx.get("high_risk_in_top") or 0)
    except (TypeError, ValueError):
        high_risk_n = 0
    try:
        excellent_good = int(ctx.get("excellent_good_in_top") or 0)
    except (TypeError, ValueError):
        excellent_good = 0

    stance = _market_overall_stance_zh(top_n, high_risk_n, excellent_good, n_total)
    if top_n == 0:
        snap = str(report.get("market_snapshot_zh") or "").strip()
        conclusion_lines = [
            f"总体：{stance}",
            f"搜索区域：{loc}",
            "当前没有可重点展开的候选房源。",
        ]
        reasons = []
        if snap:
            reasons.append(snap[:200] + ("…" if len(snap) > 200 else ""))
        reasons.extend(
            [
                "样本太少或条件偏严时，不适合急着下结论。",
                "可以稍微放宽区域、预算或卧室数，再搜一轮。",
            ]
        )
        reasons = reasons[:5]
        suggestions = [
            "调整筛选条件后重新搜索，把选择面做大一点。",
            "有目标区域后，在常见租房网站上用地图模式浏览一圈。",
            "看到合适的先收藏，再挑两三套集中联系。",
        ]
        empty_fu = {"final_score": 0.0, "price_score": 3.0, "risk_flag": False, "has_multiple_options": False}
        return _format_analysis_block_zh(
            conclusion_lines=conclusion_lines,
            reasons=reasons,
            suggestions=suggestions,
            questions=generate_followup_questions(empty_fu),
        )

    bo = star_final_verdict.get("best_overall")
    best_title = _str(bo.get("title")) if isinstance(bo, dict) else _str(items[0].get("title")) or "排序第一套"
    best_line = (bo.get("line") if isinstance(bo, dict) else None) or (
        f"综合星级和租金表现，「{best_title}」更值得优先深入了解。"
    )

    conclusion_lines = [
        f"总体：{stance}",
        f"最佳房源推荐：「{best_title}」",
        f"为什么选它：{str(best_line).strip()}",
    ]
    if top_n >= 2:
        conclusion_lines.append("多套对比时，请优先把精力放在上面这套上。")

    reasons: list[str] = []
    snap = str(report.get("market_snapshot_zh") or "").strip()
    if snap:
        reasons.append(snap.split("。")[0] + "。" if "。" in snap else snap[:120] + "…")
    reasons.append(best_line)
    for x in (report.get("best_opportunities") or [])[:2]:
        if isinstance(x, str) and x.strip():
            zh = _en_bullet_to_zh_market(x)
            if zh not in reasons:
                reasons.append(zh)
    oa = str(star_final_verdict.get("overall_advice") or "").strip()
    if oa and oa not in " ".join(reasons):
        reasons.append(oa[:160] + ("…" if len(oa) > 160 else ""))
    adv = str(report.get("overall_recommendation") or "")
    if "caution" in adv.lower() or "verify" in adv.lower():
        reasons.append("前几名里仍有个别信息需要你在原站核实，别跳过这一步。")
    reasons = _uniq_str([r for r in reasons if r])[:5]
    while len(reasons) < 3:
        reasons.append("建议把星级高的当作优先约看对象，再决定是否出价。")
        if len(reasons) >= 3:
            break

    suggestions: list[str] = []
    for x in (report.get("what_to_do_next") or [])[:4]:
        if not isinstance(x, str):
            continue
        low = x.lower()
        if "compare" in low or "shortlist" in low:
            suggestions.append("先收藏 3～5 套，按租金和地段排个优先级。")
        elif "portal" in low or "open" in low:
            suggestions.append("逐一点开原广告，核对照片、地址和是否还在招租。")
        elif "map" in low or "commute" in low:
            suggestions.append("把邮编放进地图里看一眼通勤和周边配套。")
        elif "deposit" in low or "fees" in low or "cost" in low:
            suggestions.append("向中介或房东问清押金、一次性费用和账单承担方式。")
        elif "broaden" in low or "filter" in low:
            suggestions.append("若可选太少，适当放宽条件再搜一轮。")
    suggestions.extend(
        [
            "主动联系中介预约看房，并问清能否议价。",
            "确认水电气网费是否包含在租金里，避免入住后扯皮。",
        ]
    )
    suggestions = _uniq_str(suggestions)[:4]

    fu = _followup_result_for_market_bundle(
        items=items,
        best_title=best_title,
        top_n=top_n,
        high_risk_n=high_risk_n,
        ranked_deals=ranked_deals,
        market_insight=market_insight,
    )
    return _format_analysis_block_zh(
        conclusion_lines=conclusion_lines,
        reasons=reasons[:5],
        suggestions=suggestions,
        questions=generate_followup_questions(fu),
    )


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

    stance = _overall_stance_zh(decision, risk_level)
    out: dict[str, Any] = {
        "title": title,
        "deal_score": round(deal_score, 2),
        "deal_tag": deal_tag,
        "decision": decision,
        "risk_level": risk_level,
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
    out["score_breakdown"] = sb
    rs = _pick_plain_reasons_zh(out, 5)
    sg = _action_lines_zh_from_en(list(out.get("action_suggestion") or []), decision)
    fq = generate_followup_questions(_followup_result_from_listing_ex(out))
    out["analysis_sections"] = {
        "stance": stance,
        "choice_line": _choice_line_for_stance_zh(stance, title),
        "reasons": rs,
        "suggestions": sg,
        "followup_questions": fq,
    }
    out["formatted_analysis_zh"] = format_single_listing_analysis_zh(out)
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
            "display_context": {
                "top_n": 0,
                "n_total": n_total,
                "high_risk_in_top": 0,
                "excellent_good_in_top": 0,
            },
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
        "display_context": {
            "top_n": top_n,
            "n_total": n_total,
            "high_risk_in_top": high_risk_n,
            "excellent_good_in_top": excellent_good,
        },
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
    report["formatted_analysis_zh"] = compose_market_analysis_display_zh(
        location=str(loc_key or ""),
        report=report,
        explanations=explanations,
        star_final_verdict=report["star_final_verdict"],
        ranked_deals=ranked,
        market_insight=insight,
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
    "compose_market_analysis_display_zh",
    "format_single_listing_analysis_zh",
    "generate_followup_questions",
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
    print("--- formatted_analysis_zh ---")
    print(rep.get("formatted_analysis_zh", ""))


if __name__ == "__main__":
    _cli_main()
