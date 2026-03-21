# P7 Phase3：多平台 pipeline 轻量测试（在 rental_app 下: python test_multi_source_pipeline.py）
from __future__ import annotations

from data.pipeline.multi_source_pipeline import (
    PIPELINE_REGISTRY,
    dedupe_normalized_listings,
    run_multi_source_pipeline,
    run_source_pipeline,
)


def test_pipeline_registry_keys():
    assert "rightmove" in PIPELINE_REGISTRY and "zoopla" in PIPELINE_REGISTRY


def test_run_source_pipeline_unknown_raises():
    try:
        run_source_pipeline("not_a_portal", query={}, limit=1, persist=False)
        raise AssertionError("expected ValueError")
    except ValueError as e:
        assert "unknown" in str(e).lower()


def test_dedupe_by_listing_id():
    rows = [
        {"source": "rightmove", "listing_id": "1", "title": "a"},
        {"source": "rightmove", "listing_id": "1", "title": "dup"},
        {"source": "zoopla", "listing_id": "2", "source_url": "https://x/2"},
    ]
    out = dedupe_normalized_listings(rows)
    assert len(out) == 2


def test_dedupe_by_url_when_no_id():
    rows = [
        {"source": "zoopla", "source_url": "https://z/a"},
        {"source": "zoopla", "source_url": "https://z/a"},
    ]
    assert len(dedupe_normalized_listings(rows)) == 1


def test_multi_source_empty_run_no_sources():
    r = run_multi_source_pipeline(sources=[], limit_per_source=1, persist=False)
    assert r["success"] is False
    assert r["sources_run"] == []
    assert r["total_raw_count"] == 0


def test_multi_source_unknown_only():
    r = run_multi_source_pipeline(sources=["unknown_x"], limit_per_source=1, persist=False)
    assert r["sources_run"] == []
    assert len(r["errors"]) >= 1


def test_multi_source_structure_no_network():
    r = run_multi_source_pipeline(
        sources=["rightmove", "zoopla"],
        query={"search_url": ""},
        limit_per_source=1,
        persist=False,
    )
    for k in (
        "success",
        "sources_run",
        "per_source_stats",
        "errors",
        "total_raw_count",
        "total_normalized_count",
        "aggregated_unique_count",
        "aggregated_listings_sample",
    ):
        assert k in r


if __name__ == "__main__":
    test_pipeline_registry_keys()
    test_run_source_pipeline_unknown_raises()
    test_dedupe_by_listing_id()
    test_dedupe_by_url_when_no_id()
    test_multi_source_empty_run_no_sources()
    test_multi_source_unknown_only()
    test_multi_source_structure_no_network()
    print("test_multi_source_pipeline: all ok")
