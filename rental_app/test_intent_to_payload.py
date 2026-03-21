"""P5 Phase3: intent → batch payload mapping (no Streamlit)."""
from __future__ import annotations

from web_ui.intent_to_payload import (
    build_analyze_raw_form_from_intent,
    build_batch_request_from_intent,
    merge_intent_metadata_for_area,
)
from web_ui.rental_intent import AgentRentalRequest


def test_merge_area_metadata() -> None:
    it = AgentRentalRequest(
        raw_query="x",
        preferred_area="Bedford",
        property_type="flat",
        furnished=True,
        source_preference="rightmove",
    )
    s = merge_intent_metadata_for_area(it)
    assert "Bedford" in s and "flat" in s and "rightmove" in s


def test_batch_payload_shape() -> None:
    it = AgentRentalRequest(raw_query="test", max_rent=1100.0, bedrooms=1)
    body = build_batch_request_from_intent(it)
    assert "properties" in body and len(body["properties"]) == 1
    p0 = body["properties"][0]
    assert p0["rent"] == 1100.0
    assert p0["bedrooms"] == 1
    assert p0["budget"] >= p0["rent"]


def test_raw_form_aligns_with_batch_numbers() -> None:
    it = AgentRentalRequest(raw_query="q", max_rent=900.0, max_commute_minutes=40)
    raw = build_analyze_raw_form_from_intent(it)
    body = build_batch_request_from_intent(it)
    assert float(raw["rent"]) == body["properties"][0]["rent"]
    assert int(raw["commute_minutes"]) == body["properties"][0]["commute_minutes"]


def test_defaults_when_sparse() -> None:
    it = AgentRentalRequest(raw_query="nothing specific")
    p = build_batch_request_from_intent(it)["properties"][0]
    assert "rent" in p and "budget" in p and "commute_minutes" in p


def main() -> None:
    test_merge_area_metadata()
    test_batch_payload_shape()
    test_raw_form_aligns_with_batch_numbers()
    test_defaults_when_sparse()
    print("test_intent_to_payload: all ok")


if __name__ == "__main__":
    main()
