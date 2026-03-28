# Phase D6：多数据源市场服务
from __future__ import annotations

from services.market_combined import (
    MarketListingUnified,
    build_listing_dedupe_key,
    choose_better_listing,
    dedupe_merge_by_key,
    fetch_market_combined,
    get_combined_market_listings,
    normalize_rightmove_listing,
    normalize_zoopla_listing,
)
from services.deal_engine import (
    analyze_listing_risks,
    build_deal_decision,
    calculate_deal_score,
    deal_tag_from_score,
    rank_deals,
)
from services.explain_engine import (
    build_listing_explanation,
    build_market_explain_bundle,
    build_market_recommendation_report,
    build_top_deals_explanations,
)
from services.market_insight import (
    analyze_bedroom_price_map,
    analyze_price_bands,
    analyze_value_candidates,
    build_market_commentary,
    build_market_decision_snapshot,
    build_market_insight,
    build_market_summary,
    get_market_analysis_bundle,
    get_market_insight,
)

__all__ = [
    "MarketListingUnified",
    "analyze_listing_risks",
    "build_deal_decision",
    "calculate_deal_score",
    "analyze_bedroom_price_map",
    "analyze_price_bands",
    "analyze_value_candidates",
    "build_listing_dedupe_key",
    "build_listing_explanation",
    "build_market_commentary",
    "build_market_decision_snapshot",
    "build_market_explain_bundle",
    "build_market_insight",
    "build_market_recommendation_report",
    "build_market_summary",
    "build_top_deals_explanations",
    "choose_better_listing",
    "deal_tag_from_score",
    "dedupe_merge_by_key",
    "fetch_market_combined",
    "get_combined_market_listings",
    "get_market_analysis_bundle",
    "get_market_insight",
    "normalize_rightmove_listing",
    "normalize_zoopla_listing",
    "rank_deals",
]
