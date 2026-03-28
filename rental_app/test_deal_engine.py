# Phase D8：deal_engine 单测（rental_app: python test_deal_engine.py）
from __future__ import annotations

from services.deal_engine import calculate_deal_score, deal_tag_from_score, rank_deals


def _insight():
    return {
        "stats": {
            "average_price_pcm": 1200.0,
            "total_listings": 3,
        },
        "bedroom_price_map": {
            "2": {"count": 2, "avg_price": 1500.0, "min_price": 1200.0, "max_price": 1800.0},
            "1": {"count": 1, "avg_price": 950.0, "min_price": 950.0, "max_price": 950.0},
        },
    }


def test_calculate_deal_score_cheap_vs_market():
    ins = _insight()
    cheap = {
        "price_pcm": 800.0,
        "bedrooms": 2,
        "postcode": "E1 1AA",
        "address": "1 St",
        "image_url": "http://x",
        "latitude": 51.0,
        "longitude": -0.1,
    }
    out = calculate_deal_score(cheap, ins)
    assert 0 <= out["deal_score"] <= 100
    assert set(out["score_breakdown"].keys()) == {
        "price_vs_market",
        "bedroom_value",
        "completeness",
        "location",
    }
    assert out["deal_score"] >= 65


def test_calculate_deal_score_none_safe():
    out = calculate_deal_score({}, {})
    assert isinstance(out["deal_score"], (int, float))
    assert 0 <= float(out["deal_score"]) <= 100


def test_deal_tags():
    assert deal_tag_from_score(85) == "excellent"
    assert deal_tag_from_score(70) == "good"
    assert deal_tag_from_score(55) == "average"
    assert deal_tag_from_score(30) == "poor"


def test_rank_deals():
    ins = _insight()
    listings = [
        {"title": "A", "price_pcm": 2000, "bedrooms": 2, "postcode": "SW1 1AA"},
        {"title": "B", "price_pcm": 900, "bedrooms": 2, "postcode": "E1 1AA", "image_url": "x"},
    ]
    r = rank_deals(listings, ins, top_n=5)
    assert len(r["top_deals"]) == 2
    assert r["top_deals"][0]["deal_score"] >= r["top_deals"][1]["deal_score"]
    assert r["average_score"] is not None
    assert sum(r["score_distribution"].values()) == 2


if __name__ == "__main__":
    test_calculate_deal_score_cheap_vs_market()
    test_calculate_deal_score_none_safe()
    test_deal_tags()
    test_rank_deals()
    print("test_deal_engine: all ok")
