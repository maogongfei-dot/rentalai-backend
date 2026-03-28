"""
Phase D8：Deal / Investment Decision Engine v1 —— 规则版单房源评分与 Top deals 排序。

独立于 D6/D7 数据抓取逻辑；仅消费 ``listing`` 与 ``get_market_insight`` 返回结构。
"""

from __future__ import annotations

import copy
import logging
from typing import Any

logger = logging.getLogger(__name__)

# 可调权重（和为 1.0）
_WEIGHTS: dict[str, float] = {
    "price_vs_market": 0.35,
    "bedroom_value": 0.25,
    "completeness": 0.25,
    "location": 0.15,
}


def _f(v: Any) -> float | None:
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


def _score_price_vs_market(listing: dict[str, Any], stats: dict[str, Any]) -> float:
    """相对市场均价：低于均价加分，显著低于均价更高分。"""
    price = _f(listing.get("price_pcm"))
    avg = _f(stats.get("average_price_pcm"))
    if price is None or price <= 0:
        return 50.0
    if avg is None or avg <= 0:
        return 50.0
    r = price / avg
    if r <= 0.75:
        return 100.0
    if r <= 0.85:
        return 90.0
    if r <= 0.95:
        return 78.0
    if r <= 1.0:
        return 65.0
    if r <= 1.08:
        return 52.0
    if r <= 1.2:
        return 38.0
    if r <= 1.35:
        return 25.0
    return max(0.0, 15.0 - min(15.0, (r - 1.35) * 40.0))


def _score_bedroom_value(listing: dict[str, Any], insight: dict[str, Any]) -> float:
    """同卧室档位均价：低于该档 avg 则加分。"""
    price = _f(listing.get("price_pcm"))
    bk = _bed_key(listing)
    bmap = insight.get("bedroom_price_map") or {}
    if price is None or price <= 0 or bk is None:
        return 50.0
    row = bmap.get(bk)
    if not isinstance(row, dict):
        return 50.0
    bavg = _f(row.get("avg_price"))
    if bavg is None or bavg <= 0:
        return 50.0
    r = price / bavg
    if r <= 0.88:
        return 100.0
    if r <= 0.95:
        return 82.0
    if r <= 1.0:
        return 68.0
    if r <= 1.1:
        return 52.0
    if r <= 1.25:
        return 35.0
    return max(0.0, 20.0 - min(20.0, (r - 1.25) * 35.0))


def _score_completeness(listing: dict[str, Any]) -> float:
    """postcode / image / coordinates / address 文本。"""
    pts = 0.0
    if (listing.get("postcode") or "").strip():
        pts += 28.0
    if (listing.get("image_url") or "").strip():
        pts += 28.0
    lat, lng = _f(listing.get("latitude")), _f(listing.get("longitude"))
    if lat is not None and lng is not None:
        pts += 28.0
    if (listing.get("address") or "").strip():
        pts += 16.0
    return min(100.0, pts)


def _score_location_signal(listing: dict[str, Any]) -> float:
    """有邮编高分；仅地址中等；皆无则低分。"""
    if (listing.get("postcode") or "").strip():
        return 100.0
    if (listing.get("address") or "").strip():
        return 55.0
    return 20.0


def calculate_deal_score(listing: dict[str, Any], market_insight: dict[str, Any]) -> dict[str, Any]:
    """
    单房源 deal 分（0–100）及子维度分（均为 0–100，便于解释）。

    ``market_insight``：与 ``get_market_insight`` 返回一致，至少使用 ``stats``、``bedroom_price_map``。
    """
    if not isinstance(listing, dict):
        listing = {}
    if not isinstance(market_insight, dict):
        market_insight = {}

    stats = market_insight.get("stats") if isinstance(market_insight.get("stats"), dict) else {}

    pv = _score_price_vs_market(listing, stats)
    bv = _score_bedroom_value(listing, market_insight)
    cp = _score_completeness(listing)
    loc = _score_location_signal(listing)

    breakdown = {
        "price_vs_market": round(pv, 2),
        "bedroom_value": round(bv, 2),
        "completeness": round(cp, 2),
        "location": round(loc, 2),
    }

    deal = (
        _WEIGHTS["price_vs_market"] * pv
        + _WEIGHTS["bedroom_value"] * bv
        + _WEIGHTS["completeness"] * cp
        + _WEIGHTS["location"] * loc
    )
    deal = max(0.0, min(100.0, deal))

    return {
        "deal_score": round(deal, 2),
        "score_breakdown": breakdown,
    }


def deal_tag_from_score(deal_score: float | None) -> str:
    """由总分映射标签（可单独复用）。"""
    s = _f(deal_score)
    if s is None:
        return "average"
    if s >= 80:
        return "excellent"
    if s >= 65:
        return "good"
    if s >= 50:
        return "average"
    return "poor"


def rank_deals(
    listings: list[dict[str, Any]],
    market_insight: dict[str, Any],
    top_n: int = 10,
) -> dict[str, Any]:
    """
    批量评分、排序，返回 Top N 及分布统计。

    每个条目在副本上附加 ``deal_score``、``deal_tag``，不修改入参原始 dict。
    """
    if not isinstance(listings, list):
        listings = []

    scored_rows: list[dict[str, Any]] = []
    scores: list[float] = []

    for raw in listings:
        if not isinstance(raw, dict):
            continue
        row = copy.deepcopy(raw)
        calc = calculate_deal_score(row, market_insight)
        ds = float(calc.get("deal_score") or 0.0)
        row["deal_score"] = ds
        row["deal_tag"] = deal_tag_from_score(ds)
        scored_rows.append(row)
        scores.append(ds)

    scored_rows.sort(key=lambda x: float(x.get("deal_score") or 0.0), reverse=True)

    dist: dict[str, int] = {"excellent": 0, "good": 0, "average": 0, "poor": 0}
    for row in scored_rows:
        t = row.get("deal_tag") or "average"
        if t in dist:
            dist[t] += 1

    avg_all = round(sum(scores) / len(scores), 2) if scores else None

    cap = max(0, int(top_n)) if top_n is not None else 10
    top = scored_rows[:cap] if cap else scored_rows

    return {
        "top_deals": top,
        "average_score": avg_all,
        "score_distribution": dist,
    }


# --- Phase D8-3 / D8-4：风险与最终决策（规则版，可扩展）---

# 风险标记（机器可读）；severity 用于聚合 risk_level
_RISK_RULES: tuple[tuple[str, str], ...] = (
    ("price_suspiciously_low", "high"),
    ("listing_url_missing", "high"),
    ("missing_location_identity", "medium"),
    ("no_image", "medium"),
    ("bedrooms_missing", "medium"),
)

_RISK_MESSAGES: dict[str, str] = {
    "price_suspiciously_low": "Price is ~30%+ below the sample average — verify against scams or bad data.",
    "listing_url_missing": "No listing URL — cannot trace source or open the original advert.",
    "missing_location_identity": "No address and no postcode — hard to verify location.",
    "no_image": "No property image in the feed — weaker confidence.",
    "bedrooms_missing": "Bedroom count missing — harder to compare like-for-like.",
}


def _aggregate_risk_level(flags: list[str]) -> str:
    sev: set[str] = set()
    for code, level in _RISK_RULES:
        if code in flags:
            sev.add(level)
    if "high" in sev:
        return "high"
    if "medium" in sev:
        return "medium"
    return "low"


def analyze_listing_risks(listing: dict[str, Any], market_insight: dict[str, Any]) -> dict[str, Any]:
    """
    单房源风险标记与等级（low / medium / high）。无数据时安全返回空标记 + low。
    """
    if not isinstance(listing, dict):
        listing = {}
    if not isinstance(market_insight, dict):
        market_insight = {}

    flags: list[str] = []
    stats = market_insight.get("stats") if isinstance(market_insight.get("stats"), dict) else {}

    price = _f(listing.get("price_pcm"))
    avg = _f(stats.get("average_price_pcm"))
    if price is not None and price > 0 and avg is not None and avg > 0:
        if price / avg <= 0.70:
            flags.append("price_suspiciously_low")

    addr_ok = bool((listing.get("address") or "").strip())
    pc_ok = bool((listing.get("postcode") or "").strip())
    if not addr_ok and not pc_ok:
        flags.append("missing_location_identity")

    if not (listing.get("image_url") or "").strip():
        flags.append("no_image")

    if _bed_key(listing) is None:
        flags.append("bedrooms_missing")

    if not (listing.get("listing_url") or "").strip():
        flags.append("listing_url_missing")

    seen: set[str] = set()
    ordered: list[str] = []
    for f in flags:
        if f not in seen:
            seen.add(f)
            ordered.append(f)

    return {
        "risk_flags": ordered,
        "risk_level": _aggregate_risk_level(ordered),
    }


def build_deal_decision(listing: dict[str, Any], market_insight: dict[str, Any]) -> dict[str, Any]:
    """
    综合 deal 分与风险规则输出 DO / CAUTION / AVOID（无 LLM）。
    """
    if not isinstance(listing, dict):
        listing = {}
    if not isinstance(market_insight, dict):
        market_insight = {}

    calc = calculate_deal_score(listing, market_insight)
    score = float(calc.get("deal_score") or 0.0)
    risk_block = analyze_listing_risks(listing, market_insight)
    risk_level = str(risk_block.get("risk_level") or "low")
    rflags = list(risk_block.get("risk_flags") or [])

    if risk_level == "high" or score < 60.0:
        decision = "AVOID"
    elif score >= 80.0 and risk_level == "low":
        decision = "DO"
    else:
        decision = "CAUTION"

    reasons: list[str] = []
    if score >= 80:
        reasons.append("Deal score is strong versus this sample.")
    elif score >= 60:
        reasons.append("Deal score is moderate — worth cross-checking details.")
    else:
        reasons.append("Deal score is weak versus this sample.")

    if risk_level == "high":
        reasons.append("Risk signals are elevated (fraud, missing source, or implausible price).")
    elif risk_level == "medium":
        reasons.append("Some listing fields are incomplete or weak for verification.")

    risks_human = [_RISK_MESSAGES.get(c, c) for c in rflags]

    summary_parts = [
        f"Deal score {score:.0f}/100.",
        f"Listing risk: {risk_level}.",
    ]
    if rflags:
        summary_parts.append("Flags: " + ", ".join(rflags) + ".")
    else:
        summary_parts.append("No rule-based red flags.")
    summary = " ".join(summary_parts)

    if decision == "DO":
        actions = [
            "Shortlist for viewings and compare with a few same-bedroom listings nearby.",
            "Confirm rent, bills, and deposit on the live portal before committing.",
        ]
    elif decision == "CAUTION":
        actions = [
            "Verify address/postcode and photos on the original site.",
            "Cross-check price against the portal and similar ads.",
        ]
    else:
        actions = [
            "Do not rely on this row alone — find a verifiable listing URL or agent contact.",
            "If the price looks too good, treat as suspicious until proven otherwise.",
        ]

    return {
        "decision": decision,
        "score": round(score, 2),
        "summary": summary,
        "reasons": reasons,
        "risks": risks_human,
        "action_suggestion": actions,
        "risk_flags": rflags,
        "risk_level": risk_level,
        "score_breakdown": calc.get("score_breakdown") or {},
    }


__all__ = [
    "analyze_listing_risks",
    "build_deal_decision",
    "calculate_deal_score",
    "deal_tag_from_score",
    "rank_deals",
]
