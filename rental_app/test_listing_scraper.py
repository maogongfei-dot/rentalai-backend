# P3 Phase4: scraper 烟测（在 rental_app 下: python test_listing_scraper.py）
from __future__ import annotations

from data.schema.listing_schema import ListingSchema
from data.scraper.listing_scraper import (
    SCRAPER_PLATFORM_ORDER,
    SCRAPER_REGISTRY,
    scrape_listings,
)


def test_registry_has_sources():
    for s in SCRAPER_PLATFORM_ORDER:
        assert s in SCRAPER_REGISTRY


def test_manual_mock_raw():
    raw = scrape_listings("manual_mock", normalized=False)
    assert isinstance(raw, list) and len(raw) >= 2
    assert all(isinstance(x, dict) for x in raw)
    assert raw[0].get("source") == "manual_mock"


def test_manual_mock_normalized():
    out = scrape_listings("manual_mock", normalized=True)
    assert len(out) >= 2
    assert all(isinstance(x, ListingSchema) for x in out)
    assert out[0].source == "manual_mock"
    assert out[0].rent_pcm is not None


def test_rightmove_empty_search_url():
    assert scrape_listings("rightmove", query={"search_url": ""}, normalized=False) == []


def test_zoopla_empty_search_url():
    assert scrape_listings("zoopla", query={"search_url": ""}, normalized=False) == []


def test_unknown_source_empty():
    assert scrape_listings("not_a_platform", normalized=False) == []


if __name__ == "__main__":
    test_registry_has_sources()
    test_manual_mock_raw()
    test_manual_mock_normalized()
    test_rightmove_empty_search_url()
    test_zoopla_empty_search_url()
    test_unknown_source_empty()
    print("test_listing_scraper: all ok")
