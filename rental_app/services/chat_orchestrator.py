"""
Phase D10-3：自然语言 → 解析 → D6–D9 编排（无 LLM）。
"""

from __future__ import annotations

import logging
import re
from typing import Any

from services.deal_engine import rank_deals
from services.explain_engine import build_market_recommendation_report, build_top_deals_explanations
from services.market_insight import build_insight_from_combined_listings, build_market_summary
from services.market_combined import get_combined_market_listings
from services.query_parser import normalize_search_filters, parse_user_housing_query

logger = logging.getLogger(__name__)


def _has_searchable_geo(
    location: str | None,
    area: str | None,
    postcode: str | None,
) -> bool:
    """
    是否具备可交给 D6 检索的地理信息：邮编、area，或含英文字母的 location（避免纯中文噪声当地名）。
    """
    if postcode and str(postcode).strip():
        return True
    if area and str(area).strip():
        return True
    if not location or not str(location).strip():
        return False
    return bool(re.search(r"[A-Za-z]", str(location)))


def _furnished_row_matches(row: dict[str, Any], pref: str) -> bool:
    fu = (row.get("furnished") or "").strip().lower()
    if not fu:
        return True
    if pref == "furnished":
        return "unfurnished" not in fu and ("furnish" in fu or "part" in fu)
    if pref == "unfurnished":
        return "unfurnished" in fu or "unfurn" in fu
    return True


def _empty_combined() -> dict[str, Any]:
    return {
        "success": True,
        "location": None,
        "total_before_dedupe": 0,
        "total_after_dedupe": 0,
        "sources_used": [],
        "listings": [],
        "errors": {},
    }


def _market_stats_from_insight(insight: dict[str, Any]) -> dict[str, Any]:
    """供前端结果页展示的扁平市场指标（与 ``market_summary`` 文案互补）。"""
    stats = insight.get("stats") if isinstance(insight.get("stats"), dict) else {}
    pb = insight.get("price_bands") if isinstance(insight.get("price_bands"), dict) else {}
    ov = insight.get("overall_analysis") if isinstance(insight.get("overall_analysis"), dict) else {}
    return {
        "total_listings": stats.get("total_listings"),
        "average_price_pcm": stats.get("average_price_pcm"),
        "median_price_pcm": stats.get("median_price_pcm"),
        "dominant_price_band": pb.get("dominant_price_band"),
        "market_price_level": ov.get("market_price_level"),
        "supply_level": ov.get("supply_level"),
        "bedroom_focus": ov.get("bedroom_focus"),
    }


def run_housing_ai_query(user_text: str) -> dict[str, Any]:
    """
    解析用户话 → 标准化参数 → D6 拉取 →（可选过滤）→ D7 insight → D8 rank → D9 explain + report。
    各步异常写入 ``errors``，不中断整链（在可能范围内返回部分结果）。
    """
    errors: dict[str, str] = {}
    message: str | None = None

    try:
        parsed = parse_user_housing_query(user_text or "")
    except Exception as exc:
        logger.exception("parse_user_housing_query failed")
        errors["parse"] = str(exc)
        parsed = {"raw_text": user_text or "", "intent": "market_search", "flags": {}}

    try:
        normalized = normalize_search_filters(parsed if isinstance(parsed, dict) else {})
    except Exception as exc:
        logger.exception("normalize_search_filters failed")
        errors["normalize"] = str(exc)
        normalized = normalize_search_filters({})

    loc = normalized.get("location")
    area = normalized.get("area")
    pc = normalized.get("postcode")
    filters_extra = normalized.get("filters") if isinstance(normalized.get("filters"), dict) else {}
    image_required = bool(filters_extra.get("image_required"))
    furnished_pref = filters_extra.get("furnished_preference")
    if furnished_pref is not None:
        furnished_pref = str(furnished_pref).strip().lower()

    try:
        top_n = max(1, min(100, int(normalized.get("limit") or 20)))
    except (TypeError, ValueError):
        top_n = 20

    if not _has_searchable_geo(loc, area, pc):
        message = "Add a location, area, or UK postcode to run a property search."
        combined = _empty_combined()
        insight = build_insight_from_combined_listings(
            combined,
            [],
            location=loc,
            area=area,
            postcode=pc,
            min_price=normalized.get("min_price"),
            max_price=normalized.get("max_price"),
            min_bedrooms=normalized.get("min_bedrooms"),
            max_bedrooms=normalized.get("max_bedrooms"),
            limit=normalized.get("limit"),
            sort_by=normalized.get("sort_by"),
        )
        try:
            ranked = rank_deals([], insight, top_n=top_n)
        except Exception as exc:
            errors["rank_deals"] = str(exc)
            ranked = {"top_deals": [], "average_score": None, "score_distribution": {}}
        try:
            explanations = build_top_deals_explanations([], insight, top_n=top_n, ranked_deals=ranked)
        except Exception as exc:
            errors["explanations"] = str(exc)
            explanations = {"count": 0, "items": []}
        try:
            report = build_market_recommendation_report(
                str(loc or pc or area or "this search"),
                insight,
                ranked,
            )
        except Exception as exc:
            errors["recommendation_report"] = str(exc)
            report = {
                "location": "",
                "summary_sentence": "Add a search area to continue.",
                "market_positioning": "",
                "overall_recommendation": "",
                "best_opportunities": [],
                "main_risks": [],
                "what_to_do_next": [],
                "buyer_strategy": [],
            }

        return {
            "success": True,
            "message": message,
            "user_text": user_text or "",
            "parsed_query": parsed,
            "normalized_filters": normalized,
            "market_summary": build_market_summary(insight),
            "market_stats": _market_stats_from_insight(insight),
            "top_deals": ranked,
            "explanations": explanations,
            "recommendation_report": report,
            "errors": errors,
        }

    combined: dict[str, Any] = _empty_combined()
    try:
        combined = get_combined_market_listings(
            location=loc,
            area=area,
            postcode=pc,
            min_price=normalized.get("min_price"),
            max_price=normalized.get("max_price"),
            min_bedrooms=normalized.get("min_bedrooms"),
            max_bedrooms=normalized.get("max_bedrooms"),
            limit=normalized.get("limit"),
            sort_by=normalized.get("sort_by"),
        )
    except Exception as exc:
        logger.exception("get_combined_market_listings failed")
        errors["combined"] = str(exc)
        combined = _empty_combined()
        combined["errors"] = {"fetch": str(exc)}

    listings: list[dict[str, Any]] = [x for x in (combined.get("listings") or []) if isinstance(x, dict)]

    if image_required:
        before = len(listings)
        listings = [L for L in listings if (L.get("image_url") or "").strip()]
        if before and not listings:
            message = "No listings with images in this sample; relax filters or disable image-only preference."

    if furnished_pref in ("furnished", "unfurnished"):
        listings = [L for L in listings if _furnished_row_matches(L, furnished_pref)]

    insight: dict[str, Any]
    try:
        insight = build_insight_from_combined_listings(
            combined,
            listings,
            location=loc,
            area=area,
            postcode=pc,
            min_price=normalized.get("min_price"),
            max_price=normalized.get("max_price"),
            min_bedrooms=normalized.get("min_bedrooms"),
            max_bedrooms=normalized.get("max_bedrooms"),
            limit=normalized.get("limit"),
            sort_by=normalized.get("sort_by"),
        )
    except Exception as exc:
        logger.exception("build_insight_from_combined_listings failed")
        errors["insight"] = str(exc)
        insight = build_insight_from_combined_listings(
            combined,
            [],
            location=loc,
            area=area,
            postcode=pc,
            min_price=normalized.get("min_price"),
            max_price=normalized.get("max_price"),
            min_bedrooms=normalized.get("min_bedrooms"),
            max_bedrooms=normalized.get("max_bedrooms"),
            limit=normalized.get("limit"),
            sort_by=normalized.get("sort_by"),
        )

    ranked: dict[str, Any]
    try:
        ranked = rank_deals(listings, insight, top_n=top_n)
    except Exception as exc:
        logger.exception("rank_deals failed")
        errors["rank_deals"] = str(exc)
        ranked = {"top_deals": [], "average_score": None, "score_distribution": {}}

    explanations: dict[str, Any]
    try:
        explanations = build_top_deals_explanations(
            listings,
            insight,
            top_n=top_n,
            ranked_deals=ranked,
        )
    except Exception as exc:
        logger.exception("build_top_deals_explanations failed")
        errors["explanations"] = str(exc)
        explanations = {"count": 0, "items": []}

    loc_key = loc or pc or area or insight.get("location")
    report: dict[str, Any]
    try:
        report = build_market_recommendation_report(loc_key, insight, ranked)
    except Exception as exc:
        logger.exception("build_market_recommendation_report failed")
        errors["recommendation_report"] = str(exc)
        report = {
            "location": str(loc_key or ""),
            "summary_sentence": "Report unavailable due to an internal error.",
            "market_positioning": "",
            "overall_recommendation": "",
            "best_opportunities": [],
            "main_risks": [],
            "what_to_do_next": [],
            "buyer_strategy": [],
            "readable_sections": {
                "market_situation": "",
                "worth_continuing": "",
                "top_opportunities": [],
                "main_risks": [],
                "next_steps": [],
            },
        }

    try:
        ms = build_market_summary(insight)
    except Exception as exc:
        logger.exception("build_market_summary failed")
        errors["market_summary"] = str(exc)
        ms = {"summary_title": "Market snapshot", "key_findings": [str(exc)]}

    return {
        "success": True,
        "message": message,
        "user_text": user_text or "",
        "parsed_query": parsed,
        "normalized_filters": normalized,
        "market_summary": ms,
        "market_stats": _market_stats_from_insight(insight),
        "top_deals": ranked,
        "explanations": explanations,
        "recommendation_report": report,
        "errors": errors,
    }


__all__ = ["run_housing_ai_query"]


def _cli_main() -> None:
    import json
    import sys

    t = " ".join(sys.argv[1:]).strip() or "London 2 bed under 2000"
    out = run_housing_ai_query(t)
    print(json.dumps(out, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    _cli_main()
