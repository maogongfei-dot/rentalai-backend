# P4 Phase5: Product 层英文文案单一来源（便于演示验收与后续维护）
from __future__ import annotations

# --- 详情面板（listing_detail_panel / listing_result_card）---
VIEW_DETAILS = "View details"

DETAIL_SECTION_OVERVIEW = "Overview"
DETAIL_SECTION_EXPLAIN = "Recommendation & explain"
DETAIL_SECTION_SCORE = "Score breakdown"
DETAIL_SECTION_RISK = "Risks & cautions"
DETAIL_SECTION_SOURCE = "Source"

DETAIL_NO_EXPLAIN_SUMMARY = "No explain summary for this run."
DETAIL_NO_REASONS = "No structured recommendation reasons extracted."
DETAIL_NO_SCORE_COMPONENTS = "No score breakdown in response (total score is on the card)."
DETAIL_NO_RISKS = "No major risks flagged in this analysis."
DETAIL_LINK_LISTING = "Open listing link"
DETAIL_WEIGHTED = "Weighted breakdown"
KEY_RECOMMENDATION_REASON = "Key recommendation reason"

# --- 卡片横幅（listing_result_card）---
TOP_PICK_BANNER = ":trophy: **Top pick #%d** — strongest match in your current filtered view."
FEATURED_IN_BATCH = "Featured in this batch"

# --- 全页标签（app_web lab）---
DISPLAY_LABELS: dict[str, str] = {
    "input_section": "Property details",
    "actions_section": "Actions",
    "validation_section": "Validation",
    "validation_intro": "Please fix the following before re-running analysis.",
    "errors_section": "Errors",
    "error_unexpected": "Unexpected error (details below).",
    "overview": "Overview",
    "score": "Property score",
    "decision": "Decision",
    "decision_caption": "High-level recommendation and confidence from the scoring engine.",
    "recommended": "Recommended reasons",
    "concerns": "Concerns",
    "risks": "Risks",
    "next_steps": "Next steps",
    "analysis_detail": "Analysis (structured detail)",
    "user_facing": "Narrative summary",
    "references": "References",
    "contract_risk": "Contract risk",
    "debug_expander": "Technical trace & debug",
    "listing_snapshot": "Listing snapshot",
    "listing_snapshot_caption": "Key facts, model score, and summary (same card pattern as batch).",
    "batch_listing_cards": "All listings",
    "batch_no_rows": "No listings in this batch response.",
    "criteria_section": "Analysis criteria",
    "criteria_empty": "No extra criteria captured (defaults may apply).",
    "batch_criteria_title": "Batch request (criteria snapshot)",
    "p4_filter_sort_title": "Filter & sort",
    "p4_showing_counts": "Showing %d of %d listings (after filters).",
    "p4_no_matches": "No matching listings — adjust filters and try again.",
    "p4_batch_ranking_expander": "Ranking table",
    "p4_batch_results_by_tier": "Results by tier",
    "p4_batch_stats_title": "Result summary",
    "p4_stat_total": "Total analyzed",
    "p4_stat_succeeded": "Succeeded",
    "p4_stat_top": "Top picks",
    "p4_stat_good": "Good matches",
    "p4_stat_review": "Review needed",
    "p4_stat_showing_caption": "Showing %d of %d listings (after filters).",
    "p4_batch_top_picks_title": "Top picks",
    "p4_batch_top_picks_caption": "Up to 3 listings: API order when available, otherwise your current sort.",
    "p4_batch_top_picks_empty": "No top picks in this view — adjust filters or check failed rows.",
    "p4_tier_good": "Good matches",
    "p4_tier_good_empty": "No listings in this section for the current filters.",
    "p4_tier_review": "Review needed",
    "p4_tier_review_empty": "No listings in this section.",
    "p4_batch_debug_bullets": "Listing #%s — debug bullets",
    "idle_analyze_hint": "Use **Load Demo Data** for samples, **Reset Form** to clear, then **Analyze Property**. Invalid inputs appear under **Validation** without crashing the app.",
    "spinner_analyze": "Running analysis…",
    "spinner_batch": "Running batch analysis…",
    "error_no_result": "No result was returned.",
    "score_missing_hint": "No property score for this run.",
    "run_status_failed": "Failed",
    "run_status_ok": "Completed",
    "run_status_partial": "Completed with issues",
    "batch_section_expander": "Batch analysis (POST /analyze-batch)",
    "batch_section_caption": "Uses the **API base URL** from the sidebar. Disabled while **Use local engine** is on.",
    "batch_results_header": "Batch results",
    "batch_comparison_title": "Comparison summary",
    "batch_risk_summary_title": "Risk summary",
    "batch_last_failed": "Last batch request failed: %s",
    "batch_tier_prereq": "Run a batch with at least one property to see tiered results.",
    "na_placeholder": "N/A",
    "unknown_error": "Unknown error",
}
