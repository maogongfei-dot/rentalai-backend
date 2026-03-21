# P6 Phase4：Rightmove pipeline 轻量测试（在 rental_app 下: python test_rightmove_pipeline.py）
from __future__ import annotations

import tempfile
from pathlib import Path

from data.normalizer.listing_normalizer import normalize_listing_payload
from data.pipeline.rightmove_pipeline import (
    _scrape_query,
    run_rightmove_pipeline,
)
from data.schema.listing_schema import is_valid_listing_payload
from data.storage import load_listings, save_listings


def test_scrape_query_strips_pipeline_keys():
    q = {"search_url": "", "save_normalized_sample": True, "headless": True}
    s = _scrape_query(q)
    assert "save_normalized_sample" not in s
    assert s.get("search_url") == ""


def test_pipeline_empty_scrape_no_persist():
    r = run_rightmove_pipeline(query={"search_url": ""}, limit=3, persist=False)
    assert r.get("success") is True
    assert r.get("raw_count") == 0
    assert r.get("normalized_count") == 0
    assert r.get("normalization_skipped") == 0
    assert r.get("sample_normalized") is None


def test_rightmove_like_raw_is_valid_after_normalize():
    raw = {
        "source": "rightmove",
        "listing_id": "999001",
        "title": "Test St",
        "price": "£1,100 pcm",
        "bedrooms": "2",
        "address": "Test Street, London, E1",
        "url": "https://www.rightmove.co.uk/properties/999001",
        "source_url": "https://www.rightmove.co.uk/properties/999001",
        "property_type": "Flat",
        "summary": "Test summary.",
    }
    L = normalize_listing_payload(raw, source="rightmove")
    assert is_valid_listing_payload(L.to_dict())
    assert L.rent_pcm == 1100.0
    assert L.listing_id == "999001"


def test_pipeline_persist_roundtrip_minimal():
    p = tempfile.NamedTemporaryFile(suffix=".json", delete=False).name
    Path(p).write_text("[]", encoding="utf-8")
    listings = normalize_listing_payload(
        {
            "source": "rightmove",
            "listing_id": "pipe_test_1",
            "price": 950,
            "bedrooms": 1,
            "address": "A St",
            "url": "https://example.com/p/1",
            "source_url": "https://example.com/p/1",
        },
        source="rightmove",
    )
    sr = save_listings([listings], file_path=p)
    assert sr.get("success") is True
    loaded = load_listings(file_path=p)
    assert any(x.listing_id == "pipe_test_1" for x in loaded)


if __name__ == "__main__":
    test_scrape_query_strips_pipeline_keys()
    test_pipeline_empty_scrape_no_persist()
    test_rightmove_like_raw_is_valid_after_normalize()
    test_pipeline_persist_roundtrip_minimal()
    print("test_rightmove_pipeline: all ok")
