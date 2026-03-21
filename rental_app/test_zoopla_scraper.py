# P7 Phase1：Zoopla scraper 轻量测试（在 rental_app 下: python test_zoopla_scraper.py）
from __future__ import annotations

from data.scraper.listing_scraper import scrape_listings
from data.scraper.zoopla_scraper import (
    DEFAULT_ZOOPLA_SEARCH_URL,
    ZooplaScraper,
    _scraper_run_config_from_query,
    listing_id_from_zoopla_href,
)


def test_listing_id_from_href():
    assert listing_id_from_zoopla_href("/to-rent/details/72518342/") == "72518342"
    assert listing_id_from_zoopla_href(None) is None


def test_config_from_query_default_url():
    cfg, flags = _scraper_run_config_from_query({}, limit=12)
    assert cfg.source == "zoopla"
    assert cfg.limit == 12
    assert cfg.search_url == DEFAULT_ZOOPLA_SEARCH_URL
    assert flags["debug"] is False


def test_empty_search_url_returns_empty():
    assert scrape_listings("zoopla", query={"search_url": ""}, limit=3) == []


def test_parse_row_keys_if_any():
    """无 Playwright/网络时允许空列表。"""
    out = ZooplaScraper().scrape(query={"search_url": ""}, limit=1)
    assert isinstance(out, list)
    if not out:
        return
    row = out[0]
    for k in (
        "source",
        "listing_id",
        "title",
        "price",
        "bedrooms",
        "address",
        "url",
        "source_url",
        "property_type",
        "summary",
    ):
        assert k in row
    assert row["source"] == "zoopla"


if __name__ == "__main__":
    test_listing_id_from_href()
    test_config_from_query_default_url()
    test_empty_search_url_returns_empty()
    test_parse_row_keys_if_any()
    print("test_zoopla_scraper: all ok")
