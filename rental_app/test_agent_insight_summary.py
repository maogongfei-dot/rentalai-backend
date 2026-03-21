"""P5 Phase4: agent insight + refinement rules (no Streamlit)."""
from __future__ import annotations

from web_ui.agent_refinement import FIELD_MAX_RENT, get_missing_intent_fields, get_refinement_suggestions
from web_ui.agent_insight_summary import build_agent_insight_bundle, resolve_intent_for_insights
from web_ui.rental_intent import AgentRentalRequest


def test_missing_fields_sparse() -> None:
    it = AgentRentalRequest(raw_query="hello")
    m = get_missing_intent_fields(it)
    assert FIELD_MAX_RENT in m
    assert len(get_refinement_suggestions(it)) >= 3


def test_bundle_batch_empty_rows() -> None:
    it = AgentRentalRequest(raw_query="x", max_rent=1000.0)
    b = build_agent_insight_bundle(it, mode="batch", batch_data={"results": []})
    assert "no listing" in b["short_summary"].lower() or "**0**" in b["short_summary"]


def test_resolve_prefers_session_intent() -> None:
    sess = {"p5_agent_last_intent": {"raw_query": "studio", "max_rent": 900}}
    it = resolve_intent_for_insights(sess, normalized_form=None)
    assert it.max_rent == 900.0


def test_bundle_single_low_score() -> None:
    it = AgentRentalRequest(raw_query="r", max_rent=800.0)
    b = build_agent_insight_bundle(
        it,
        mode="single",
        single_result={"success": True, "property_score": 40.0},
    )
    assert any("low" in (c or "").lower() for c in b["caution_items"])


def main() -> None:
    test_missing_fields_sparse()
    test_bundle_batch_empty_rows()
    test_resolve_prefers_session_intent()
    test_bundle_single_low_score()
    print("test_agent_insight_summary: all ok")


if __name__ == "__main__":
    main()
