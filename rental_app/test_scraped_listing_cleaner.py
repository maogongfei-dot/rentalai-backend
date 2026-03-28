# Phase D4：抓取清洗层单测（在 rental_app 下: python test_scraped_listing_cleaner.py）
from __future__ import annotations

from data.scraped_listing_cleaner import (
    clean_scraped_listings,
    enrich_scraped_listing_defaults,
    get_last_scrape_clean_stats,
    is_valid_scraped_listing,
    prepare_scraped_listings_for_recommendation,
)


def test_dedupe_by_listing_id_and_url():
    raw = [
        {
            "listing_id": "111",
            "title": "A",
            "rent": 1000,
            "source_url": "https://www.zoopla.co.uk/to-rent/details/111/",
            "postcode": "E1 6LS",
        },
        {
            "listing_id": "111",
            "title": "A dup",
            "rent": 1000,
            "source_url": "https://www.zoopla.co.uk/to-rent/details/111/",
            "postcode": "E1 6LS",
        },
        {
            "listing_id": "222",
            "title": "B",
            "rent": 1100,
            "source_url": "https://www.zoopla.co.uk/to-rent/details/222/",
            "postcode": "E1 6LS",
        },
    ]
    out = clean_scraped_listings(raw, source="zoopla")
    assert len(out) == 2
    stats = get_last_scrape_clean_stats()
    assert stats["deduped_count"] == 1
    assert stats["raw_count"] == 3


def test_dedupe_title_postcode_rent():
    raw = [
        {
            "listing_id": "a1",
            "title": "Same Flat",
            "rent": "£1,250 pcm",
            "source_url": "https://www.zoopla.co.uk/to-rent/details/a1/",
            "postcode": "sw1a 1aa",
        },
        {
            "listing_id": "a2",
            "title": "same   flat",
            "rent": 1250,
            "source_url": "https://www.zoopla.co.uk/to-rent/details/a2/",
            "postcode": "SW1A 1AA",
        },
    ]
    out = clean_scraped_listings(raw, source="zoopla")
    assert len(out) == 1
    assert get_last_scrape_clean_stats()["deduped_count"] == 1


def test_rent_formats():
    r = enrich_scraped_listing_defaults(
        {
            "listing_id": "x",
            "title": "T",
            "source_url": "https://x/",
            "rent": "£1,500",
        },
        source="zoopla",
    )
    from data.scraped_listing_cleaner import _clean_scraped_fields

    c = _clean_scraped_fields(r)
    assert c["rent"] == 1500.0

    r2 = _clean_scraped_fields(
        enrich_scraped_listing_defaults(
            {"listing_id": "y", "title": "T2", "source_url": "https://y/", "price": "1250"},
            source="zoopla",
        )
    )
    assert r2["rent"] == 1250.0


def test_bedrooms_text():
    from data.scraped_listing_cleaner import _clean_bedrooms_value

    assert _clean_bedrooms_value("2 bedrooms") == 2.0
    assert _clean_bedrooms_value("1 bed") == 1.0
    assert _clean_bedrooms_value("studio flat") == 0.0
    assert _clean_bedrooms_value(2) == 2.0


def test_invalid_dropped():
    bad = [
        {"listing_id": "z", "title": "", "rent": 100, "source_url": "https://a/"},
        {"listing_id": "z2", "title": "ok", "rent": None, "source_url": "https://a/"},
        {"listing_id": "z3", "title": "only title", "rent": 500, "source_url": "https://b/"},
    ]
    out = clean_scraped_listings(bad, source="zoopla")
    assert len(out) == 1
    assert out[0].get("listing_id") == "z3"
    st = get_last_scrape_clean_stats()
    assert st["dropped_invalid"] == 2


def test_prepare_produces_canonical_keys():
    raw = [
        {
            "listing_id": "90000001",
            "title": "Flat",
            "rent_pcm": 1100.0,
            "source": "zoopla",
            "source_url": "https://www.zoopla.co.uk/to-rent/details/90000001/",
            "postcode": "E1 6LS",
            "city": "London",
        }
    ]
    canon = prepare_scraped_listings_for_recommendation(raw, source="zoopla")
    assert len(canon) == 1
    row = canon[0]
    assert "listing_title" in row
    assert row.get("rent") == 1100.0
    assert row.get("source") == "zoopla"


def test_is_valid():
    assert is_valid_scraped_listing(
        {"listing_title": "x", "rent": 1, "listing_id": "1", "source_url": "http://a"}
    )
    assert not is_valid_scraped_listing({"listing_title": "x", "rent": 1})
    assert not is_valid_scraped_listing({"title": "x", "listing_id": "1"})


def test_run_ai_zoopla_smoke():
    from ai_recommendation_bridge import run_ai_analyze_zoopla

    out = run_ai_analyze_zoopla("1 bed flat in London under 2000 pcm")
    assert out.get("success") is not False
    recs = out.get("recommendations") or []
    assert isinstance(recs, list)
    summ = out.get("summary") or {}
    assert summ.get("source_mode")
    assert isinstance(summ.get("scrape_clean_stats"), dict)


if __name__ == "__main__":
    test_dedupe_by_listing_id_and_url()
    test_dedupe_title_postcode_rent()
    test_rent_formats()
    test_bedrooms_text()
    test_invalid_dropped()
    test_prepare_produces_canonical_keys()
    test_is_valid()
    test_run_ai_zoopla_smoke()
    print("test_scraped_listing_cleaner: all ok")
