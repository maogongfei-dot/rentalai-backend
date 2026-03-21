# P6 Phase2：探针结构烟测（不依赖真实联网成功）
# 在 rental_app 下: python test_playwright_probe.py
from __future__ import annotations

from data.scraper.scraper_config import ScraperRunConfig
from data.scraper.playwright_runner import (
    playwright_available,
    run_playwright_page_probe,
)


def _assert_probe_shape(d: dict) -> None:
    for k in (
        "success",
        "source",
        "url",
        "final_url",
        "page_title",
        "html_length",
        "error",
    ):
        assert k in d


def test_playwright_available_is_bool():
    assert isinstance(playwright_available(), bool)


def test_probe_empty_url():
    cfg = ScraperRunConfig(source="rightmove", search_url="")
    r = run_playwright_page_probe(cfg)
    _assert_probe_shape(r)
    assert r["success"] is False
    assert r["error"]
    assert r["final_url"] is None
    assert r["page_title"] is None
    assert r["html_length"] is None


def test_scraper_config_to_runner_kwargs():
    cfg = ScraperRunConfig(
        source="rightmove",
        search_url="https://example.com/",
        query={"k": 1},
        max_pages=2,
        limit=5,
        headless=False,
        save_raw_html=True,
        save_screenshots=True,
        output_dir="/tmp/x",
    )
    kw = cfg.to_runner_kwargs()
    assert kw["source"] == "rightmove"
    assert kw["search_url"] == "https://example.com/"
    assert kw["query"] == {"k": 1}
    assert kw["max_pages"] == 2
    assert kw["limit"] == 5
    assert kw["headless"] is False
    assert kw["save_raw_html"] is True
    assert kw["save_screenshots"] is True
    assert kw["output_dir"] == "/tmp/x"


if __name__ == "__main__":
    test_playwright_available_is_bool()
    test_probe_empty_url()
    test_scraper_config_to_runner_kwargs()
    print("test_playwright_probe: all ok")
