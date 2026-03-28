# Phase D7：market_insight 单测（rental_app: python test_market_insight.py）
from __future__ import annotations

from services.market_insight import (
    analyze_bedroom_price_map,
    analyze_price_bands,
    analyze_value_candidates,
    get_market_insight,
)


def _sample_listings():
    return [
        {
            "source": "zoopla",
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
            "title": "B",
            "price_pcm": 1200,
            "bedrooms": 2,
            "property_type": "Flat",
            "postcode": "E1 1AA",
            "address": "2 Test St",
        },
        {
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


if __name__ == "__main__":
    test_analyze_price_bands()
    test_analyze_bedroom_price_map()
    test_analyze_value_candidates()
    test_get_market_insight_smoke()
    print("test_market_insight: all ok")
