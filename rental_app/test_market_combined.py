# Phase D6-3/D6-4：market_combined 去重合并、排序、服务与 API 逻辑（rental_app 下: python test_market_combined.py）
from __future__ import annotations

from services.market_combined import (
    choose_better_listing,
    dedupe_merge_by_key,
    fetch_market_combined,
    normalize_rightmove_listing,
    normalize_zoopla_listing,
)


def test_choose_better_listing_prefers_complete():
    sparse = normalize_zoopla_listing(
        {
            "listing_id": "a",
            "title": "x",
            "rent_pcm": 1000,
            "bedrooms": 1,
            "address": "Short",
            "postcode": "E1 1AA",
            "source_url": "https://z.example/a",
        }
    )
    rich = normalize_zoopla_listing(
        {
            "listing_id": "b",
            "title": "y",
            "rent_pcm": 1000,
            "bedrooms": 1,
            "address": "Much longer address line for scoring",
            "postcode": "E1 1AA",
            "summary": "A" * 50,
            "source_url": "https://z.example/b",
        }
    )
    assert choose_better_listing(sparse, rich) is rich


def test_dedupe_merge_combined_two_sources():
    z = normalize_zoopla_listing(
        {
            "listing_id": "z1",
            "title": "Same flat",
            "rent_pcm": 1200,
            "bedrooms": 2,
            "address": "10 Example Street, London",
            "postcode": "SW1A 1AA",
            "source_url": "https://www.zoopla.co.uk/to-rent/details/1/",
        }
    )
    r = normalize_rightmove_listing(
        {
            "listing_id": "r9",
            "title": "Same flat",
            "rent_pcm": 1200,
            "bedrooms": 2,
            "address": "10 Example Street, London",
            "postcode": "SW1A 1AA",
            "source_url": "https://www.rightmove.co.uk/properties/r9",
            "summary": "Extra blurb from Rightmove only.",
        }
    )
    assert z.get("dedupe_key") and z["dedupe_key"] == r.get("dedupe_key")
    merged = dedupe_merge_by_key([z, r])
    assert len(merged) == 1
    m = merged[0]
    assert m["source"] == "combined"
    assert set(m["source_names"]) == {"rightmove", "zoopla"}
    assert m["matched_sources_count"] == 2
    assert len(m["matched_sources"]) == 2


def test_sort_newest():
    from services.market_combined import _sort_listings

    rows = [
        {"added_date": "2025-01-01", "price_pcm": 100},
        {"added_date": "2025-06-01", "price_pcm": 200},
        {"added_date": None, "price_pcm": 50},
    ]
    s = _sort_listings(rows, "newest")
    assert s[0]["added_date"] == "2025-06-01"


def test_fetch_market_combined_smoke_prints():
    r = fetch_market_combined(location="London", max_price=3000, limit=20, sort_by="price_asc")
    print("merge_before", r["total_before_dedupe"], "after", r["total_after_dedupe"], "errors", r.get("errors"))
    for row in (r.get("listings") or [])[:3]:
        print(
            row.get("source"),
            row.get("source_names"),
            row.get("title"),
            row.get("price_pcm"),
            row.get("address"),
        )
    assert "listings" in r
    assert "total_before_dedupe" in r
    assert "total_after_dedupe" in r


if __name__ == "__main__":
    test_choose_better_listing_prefers_complete()
    test_dedupe_merge_combined_two_sources()
    test_sort_newest()
    test_fetch_market_combined_smoke_prints()
    print("test_market_combined: all ok")
