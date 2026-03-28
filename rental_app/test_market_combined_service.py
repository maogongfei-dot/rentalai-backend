# Phase D6：market_combined 服务单测（在 rental_app 下: python test_market_combined_service.py）
from __future__ import annotations

from services.market_combined import (
    build_listing_dedupe_key,
    fetch_market_combined,
    normalize_rightmove_listing,
    normalize_zoopla_listing,
)


def test_build_dedupe_key_priority():
    a = {
        "postcode": "SW1A 1AA",
        "price_pcm": 1500.0,
        "bedrooms": 2,
        "address": "10 Downing St, London",
        "source": "zoopla",
        "source_listing_id": "1",
    }
    k1 = build_listing_dedupe_key(a)
    assert k1 and "p:SW1A 1AA" in k1

    b = {"address": "Foo Bar", "price_pcm": 900, "bedrooms": 1, "source": "x", "source_listing_id": "9"}
    k2 = build_listing_dedupe_key(b)
    assert k2 and "a:" in k2

    c = {"source": "rightmove", "source_listing_id": "12345"}
    k3 = build_listing_dedupe_key(c)
    assert k3 == "s:rightmove|id:12345"


def test_normalize_zoopla():
    raw = {
        "listing_id": "z1",
        "title": "Flat",
        "rent_pcm": 1200,
        "bedrooms": 2,
        "address": "1 Test St",
        "postcode": "E1 1AA",
        "source": "zoopla",
        "source_url": "https://zoopla.example/1",
    }
    u = normalize_zoopla_listing(raw)
    assert u["source"] == "zoopla"
    assert u["price_pcm"] == 1200.0
    assert u["dedupe_key"]


def test_normalize_rightmove():
    raw = {
        "listing_id": "rm1",
        "title": "House",
        "rent_pcm": 800,
        "bedrooms": "2",
        "address": "x",
        "source_url": "https://rightmove.example/p/1",
    }
    u = normalize_rightmove_listing(raw)
    assert u["source"] == "rightmove"
    assert u["bedrooms"] == 2


def test_fetch_market_combined_smoke():
    r = fetch_market_combined(location="London", max_price=2000, limit=10, sort_by="price_asc")
    assert "listings" in r
    assert "errors" in r
    assert "total_before_dedupe" in r
    assert "total_after_dedupe" in r
    assert isinstance(r["listings"], list)


if __name__ == "__main__":
    test_build_dedupe_key_priority()
    test_normalize_zoopla()
    test_normalize_rightmove()
    test_fetch_market_combined_smoke()
    print("test_market_combined_service: all ok")
