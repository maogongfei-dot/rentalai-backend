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


__all__ = [
    "calculate_deal_score",
    "deal_tag_from_score",
    "rank_deals",
]
