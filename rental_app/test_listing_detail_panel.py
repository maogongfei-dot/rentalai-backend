# P4 Phase3: 详情 bundle 构建烟测（无 Streamlit）
from __future__ import annotations

from web_ui.listing_detail_panel import build_analyze_detail_bundle, build_batch_detail_bundle


def test_batch_failed_bundle():
    b = build_batch_detail_bundle({"index": 0, "success": False, "error": {"message": "x"}, "input_meta": {}})
    assert b["ok"] is False
    assert b["error_message"] == "x"


def test_analyze_bundle_has_overview():
    r = {
        "success": True,
        "property_score": 50.0,
        "top_house_export": {"scores": {"price": 10, "commute": 8}, "explain": {"weighted_breakdown": {}}},
        "explanation_summary": {"summary": "OK", "key_positives": ["a"]},
        "unified_decision_payload": {
            "status": {"overall_recommendation": "Go"},
            "decision": {},
            "analysis": {"primary_blockers": ["watch"]},
            "user_facing": {},
            "trace": {},
        },
    }
    ctx = {"rent": 1000, "bedrooms": 1, "postcode": "E1"}
    b = build_analyze_detail_bundle(r, ctx)
    assert b["overview"]["title"]
    assert b["explain_summary_text"] == "OK"
    assert len(b["score_component_lines"]) >= 1


if __name__ == "__main__":
    test_batch_failed_bundle()
    test_analyze_bundle_has_overview()
    print("test_listing_detail_panel: all ok")
