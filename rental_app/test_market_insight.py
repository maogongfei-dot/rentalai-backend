# Phase D7：market_insight 单测（rental_app: python test_market_insight.py）
from __future__ import annotations

from services.market_insight import (
    analyze_bedroom_price_map,
    analyze_price_bands,
    analyze_value_candidates,
    build_market_decision_snapshot,
    build_market_summary,
    get_market_analysis_bundle,
    get_market_insight,
)


def _sample_listings():
    return [
        {
            "source": "zoopla",
            "source_listing_id": "z1",
            "title": "A",
            "price_pcm": 950,
            "bedrooms": 1,
            "property_type": "Flat",
            "postcode": "E1 1AA",
            "address": "1 Test St",
            "furnished": "furnished",
            "image_url": "http://x/img.jpg",
            "latitude": 51.5,
            "longitude": -0.1,
        },
        {
            "source": "rightmove",
            "source_listing_id": "r2",
            "title": "B",
            "price_pcm": 1200,
            "bedrooms": 2,
            "property_type": "Flat",
            "postcode": "E1 1AA",
            "address": "2 Test St",
        },
        {
            "source_listing_id": "z3",
            "title": "C",
            "price_pcm": 1800,
            "bedrooms": 2,
            "property_type": "House",
            "postcode": "SW1 1AA",
            "address": "3 Other Rd",
        },
    ]


def test_analyze_price_bands():
    r = analyze_price_bands(_sample_listings())
    assert r["budget_band_counts"]["under_1000"] == 1
    assert r["dominant_price_band"]


def test_analyze_bedroom_price_map():
    m = analyze_bedroom_price_map(_sample_listings())
    assert "1" in m and "2" in m
    assert m["2"]["count"] == 2


def test_analyze_value_candidates():
    vc = analyze_value_candidates(_sample_listings(), top_n=3)
    assert isinstance(vc, list)


def test_get_market_insight_smoke():
    from unittest.mock import patch

    fake_combined = {
        "success": True,
        "location": "London",
        "total_before_dedupe": 3,
        "total_after_dedupe": 3,
        "sources_used": ["zoopla", "rightmove"],
        "listings": _sample_listings(),
        "errors": {},
    }
    with patch("services.market_combined.get_combined_market_listings", return_value=fake_combined):
        out = get_market_insight(location="London", max_price=2500, limit=15)
    assert out.get("success") is True
    assert out["stats"]["total_listings"] == 3
    assert out["stats"]["median_price_pcm"] is not None
    assert "overall_analysis" in out
    assert len(out["value_candidates"]) >= 1


def test_build_market_summary_empty():
    from unittest.mock import patch

    fake = {"success": True, "listings": [], "sources_used": [], "errors": {}, "location": "X"}
    with patch("services.market_combined.get_combined_market_listings", return_value=fake):
        empty = get_market_insight(location="X")
    s = build_market_summary(empty)
    assert s["summary_title"]
    assert "empty_sample" in (s.get("risk_flags") or [])


def test_build_market_summary_and_decision_with_data():
    from unittest.mock import patch

    fake_combined = {
        "success": True,
        "location": "London",
        "total_before_dedupe": 3,
        "total_after_dedupe": 3,
        "sources_used": ["zoopla"],
        "listings": _sample_listings(),
        "errors": {},
    }
    with patch("services.market_combined.get_combined_market_listings", return_value=fake_combined):
        ins = get_market_insight(location="London", max_price=3000)
    sm = build_market_summary(ins)
    assert sm.get("recommendation")
    assert sm.get("price_summary")
    ds = build_market_decision_snapshot(ins)
    assert ds.get("conclusion")
    assert "top_value_listing_titles" in ds


def test_get_market_analysis_bundle():
    from unittest.mock import patch

    fake_combined = {
        "success": True,
        "location": "London",
        "total_before_dedupe": 3,
        "total_after_dedupe": 3,
        "sources_used": ["zoopla", "rightmove"],
        "listings": _sample_listings(),
        "errors": {},
    }
    with patch("services.market_combined.get_combined_market_listings", return_value=fake_combined):
        b = get_market_analysis_bundle(location="London", max_price=3000)
    assert b["success"] is True
    assert "insight" in b and "summary" in b and "decision_snapshot" in b
    assert b["summary"]["key_findings"]


def test_print_bundle_snapshot():
    """最小演示：打印关键字段（仍用 mock）。"""
    from unittest.mock import patch

    fake_combined = {
        "success": True,
        "location": "London",
        "total_before_dedupe": 3,
        "total_after_dedupe": 3,
        "sources_used": ["zoopla"],
        "listings": _sample_listings(),
        "errors": {},
    }
    with patch("services.market_combined.get_combined_market_listings", return_value=fake_combined):
        b = get_market_analysis_bundle(location="London", max_price=3000)
    ins = b["insight"]
    print(
        "total_listings",
        ins["stats"]["total_listings"],
        "avg_pcm",
        ins["stats"].get("average_price_pcm"),
        "dominant_band",
        ins["price_bands"].get("dominant_price_band"),
    )
    print("recommendation", b["summary"].get("recommendation"))


if __name__ == "__main__":
    test_analyze_price_bands()
    test_analyze_bedroom_price_map()
    test_analyze_value_candidates()
    test_get_market_insight_smoke()
    test_build_market_summary_empty()
    test_build_market_summary_and_decision_with_data()
    test_get_market_analysis_bundle()
    test_print_bundle_snapshot()
    print("test_market_insight: all ok")
