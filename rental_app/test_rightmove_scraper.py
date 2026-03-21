# P6 Phase3：Rightmove 轻量结构测试（不依赖列表页联网成功）
# 在 rental_app 下: python test_rightmove_scraper.py
from __future__ import annotations

from data.scraper.listing_scraper import scrape_listings
from data.scraper.rightmove_scraper import (
    DEFAULT_RIGHTMOVE_SEARCH_URL,
    RightmoveScraper,
    _scraper_run_config_from_query,
    listing_id_from_property_href,
)


def test_listing_id_from_href():
    assert listing_id_from_property_href("/properties/12345#/?channel=RES_LET") == "12345"
    assert listing_id_from_property_href(None) is None
    assert listing_id_from_property_href("/foo") is None


def test_scraper_config_from_query_preserves_limit():
    cfg, flags = _scraper_run_config_from_query({"headless": False}, limit=7)
    assert cfg.limit == 7
    assert cfg.headless is False
    assert cfg.search_url == DEFAULT_RIGHTMOVE_SEARCH_URL
    assert "debug" not in cfg.query
    assert flags["debug"] is False


def test_empty_search_url_returns_empty():
    out = scrape_listings("rightmove", query={"search_url": ""}, limit=5)
    assert out == []


def test_rightmove_row_shape_if_any():
    """联网且环境正常时会有数据；无 Playwright/网络时允许空列表。"""
    out = RightmoveScraper().scrape(query={"search_url": ""}, limit=1)
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
        "property_type",
        "summary",
    ):
        assert k in row
    assert row["source"] == "rightmove"


if __name__ == "__main__":
    test_listing_id_from_href()
    test_scraper_config_from_query_preserves_limit()
    test_empty_search_url_returns_empty()
    test_rightmove_row_shape_if_any()
    print("test_rightmove_scraper: all ok")
