# P4 Phase1: 卡片模型构建烟测（无 Streamlit 渲染）
from __future__ import annotations

from web_ui.listing_result_card import build_analyze_card_model, build_batch_row_card_model


def test_analyze_model_uses_context_and_score():
    r = {
        "success": True,
        "property_score": 72.5,
        "unified_decision_payload": {
            "status": {"overall_recommendation": "Proceed — good fit for budget"},
            "decision": {"final_summary": "Looks reasonable."},
            "user_facing": {"summary": "Solid match"},
        },
        "explanation_summary": {"summary": "Engine summary line"},
    }
    ctx = {"rent": 1200, "bedrooms": 2, "postcode": "E1 1AA", "bills_included": True}
    m = build_analyze_card_model(r, listing_context=ctx)
    assert m["title"] == "Solid match"
    assert "72.50" in m["final_score"] or m["final_score"] == "72.50"
    assert m["badge_kind"] == "recommended"
    assert m["rent_pcm"] == 1200


def test_batch_row_failed():
    row = {
        "index": 0,
        "success": False,
        "error": {"message": "bad input"},
        "input_meta": {"rent": 500},
    }
    m = build_batch_row_card_model(row)
    assert m["ok"] is False
    assert "failed" in m["title"].lower()


def test_batch_row_top_highlight():
    row = {
        "index": 1,
        "success": True,
        "score": 80,
        "decision_code": "recommended",
        "status": {},
        "decision": {},
        "user_facing": {"summary": "Nice"},
        "explanation_summary": {},
        "analysis": {},
        "trace": {},
        "references": {},
        "recommended_reasons": ["A", "B"],
        "input_meta": {"rent": 1000, "bedrooms": 1, "bills_included": False},
    }
    m = build_batch_row_card_model(row, highlight_top=True)
    assert m["highlight_top"] is True
    assert m["badge_label"] == "Recommended"


if __name__ == "__main__":
    test_analyze_model_uses_context_and_score()
    test_batch_row_failed()
    test_batch_row_top_highlight()
    print("test_listing_result_card: all ok")
