# Phase D8：deal_engine 单测（rental_app: python test_deal_engine.py）
from __future__ import annotations

from collections import Counter

from services.deal_engine import (
    analyze_listing_risks,
    build_deal_decision,
    calculate_deal_score,
    deal_tag_from_score,
    rank_deals,
)


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


def test_analyze_listing_risks():
    ins = _insight()
    high_price = {"price_pcm": 700, "bedrooms": 2, "listing_url": "http://x", "postcode": "E1", "image_url": "i"}
    r = analyze_listing_risks(high_price, ins)
    assert "price_suspiciously_low" in r["risk_flags"]
    assert r["risk_level"] == "high"

    no_url = {
        "price_pcm": 1200,
        "bedrooms": 2,
        "postcode": "E1",
        "image_url": "i",
        "address": "1 St",
    }
    assert analyze_listing_risks(no_url, ins)["risk_level"] == "high"
    assert "listing_url_missing" in analyze_listing_risks(no_url, ins)["risk_flags"]


def test_build_deal_decision():
    ins = _insight()
    good = {
        "price_pcm": 900,
        "bedrooms": 2,
        "postcode": "E1 1AA",
        "address": "1 St",
        "image_url": "http://i",
        "latitude": 51.0,
        "longitude": -0.1,
        "listing_url": "http://listing",
    }
    out = build_deal_decision(good, ins)
    assert out["decision"] in ("DO", "CAUTION", "AVOID")
    assert "summary" in out and out["reasons"]
    assert isinstance(out["risks"], list)
    assert isinstance(out["action_suggestion"], list)


def _demo_prints() -> None:
    """Synthetic demo: Top 5 deal_score, decision mix, risk flag examples."""
    ins = _insight()
    listings = [
        {
            "title": "Cheap",
            "price_pcm": 700,
            "bedrooms": 2,
            "postcode": "E1",
            "address": "A",
            "image_url": "u",
            "listing_url": "http://l",
        },
        {
            "title": "No bed",
            "price_pcm": 1100,
            "postcode": "SW1",
            "address": "B",
            "image_url": "u",
            "listing_url": "http://l",
        },
        {
            "title": "No url",
            "price_pcm": 1100,
            "bedrooms": 1,
            "postcode": "N1",
            "address": "C",
            "image_url": "u",
        },
        {
            "title": "Strong",
            "price_pcm": 950,
            "bedrooms": 2,
            "postcode": "E2",
            "address": "D",
            "image_url": "u",
            "latitude": 51.0,
            "longitude": -0.1,
            "listing_url": "http://l",
        },
    ]
    ranked = rank_deals(listings, ins, top_n=5)
    top5 = ranked["top_deals"][:5]
    print("--- Top deal_score (up to 5) ---")
    for i, row in enumerate(top5, 1):
        print(f"  {i}. {row.get('title')!s} deal_score={row.get('deal_score')}")

    decisions = []
    risk_seen: list[str] = []
    for row in top5:
        d = build_deal_decision(row, ins)
        decisions.append(d["decision"])
        risk_seen.extend(d.get("risk_flags") or [])

    print("--- Decision distribution ---")
    for k, v in Counter(decisions).items():
        print(f"  {k}: {v}")

    print("--- risk_flags (deduped examples) ---")
    seen: set[str] = set()
    for f in risk_seen:
        if f not in seen:
            seen.add(f)
            print(f"  - {f}")


if __name__ == "__main__":
    test_calculate_deal_score_cheap_vs_market()
    test_calculate_deal_score_none_safe()
    test_deal_tags()
    test_rank_deals()
    test_analyze_listing_risks()
    test_build_deal_decision()
    print("test_deal_engine: all ok")
    _demo_prints()
