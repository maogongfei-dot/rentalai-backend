"""P5 Phase2: rule-based parse_rental_intent tests (no Streamlit)."""
from __future__ import annotations

from web_ui.agent_intent_mock_parser import parse_rental_intent_mock
from web_ui.rental_intent import AgentRentalRequest
from web_ui.rental_intent_parser import intent_has_key_signals, parse_rental_intent


def test_empty() -> None:
    r = parse_rental_intent("")
    assert r.raw_query == ""
    assert r.max_rent is None


def test_mock_alias_matches() -> None:
    assert parse_rental_intent_mock("x").raw_query == parse_rental_intent("x").raw_query


def test_example_east_london() -> None:
    r = parse_rental_intent(
        "I need a furnished flat in East London under £1500",
    )
    assert r.max_rent == 1500.0
    assert r.furnished is True
    assert r.property_type == "flat"
    assert r.preferred_area and "east london" in r.preferred_area.lower()
    assert intent_has_key_signals(r)


def test_example_chinese_mixed() -> None:
    r = parse_rental_intent("预算1200，想找一居，包bill，Bedford附近")
    assert r.max_rent == 1200.0
    assert r.bedrooms == 1
    assert r.bills_included is True
    assert r.preferred_area and "bedford" in r.preferred_area.lower()
    assert intent_has_key_signals(r)


def test_example_studio_mk9_commute() -> None:
    r = parse_rental_intent("studio near MK9, commute within 30 mins")
    assert r.property_type == "studio"
    assert r.bedrooms == 0
    assert r.target_postcode == "MK9"
    assert r.max_commute_minutes == 30
    assert intent_has_key_signals(r)


def test_example_rightmove_room() -> None:
    r = parse_rental_intent("Need a room on Rightmove")
    assert r.property_type == "room"
    assert r.source_preference == "rightmove"
    assert intent_has_key_signals(r)


def test_from_dict_roundtrip() -> None:
    d = parse_rental_intent("£900 pcm 2 bed").to_dict()
    r2 = AgentRentalRequest.from_dict(d)
    assert r2.max_rent == 900.0
    assert r2.bedrooms == 2


def test_sparse_no_crash() -> None:
    r = parse_rental_intent("maybe something vague")
    assert r.raw_query == "maybe something vague"
    assert not intent_has_key_signals(r)


def main() -> None:
    test_empty()
    test_mock_alias_matches()
    test_example_east_london()
    test_example_chinese_mixed()
    test_example_studio_mk9_commute()
    test_example_rightmove_room()
    test_from_dict_roundtrip()
    test_sparse_no_crash()
    print("test_rental_intent_parser: all ok")


if __name__ == "__main__":
    main()
