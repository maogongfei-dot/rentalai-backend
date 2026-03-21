# P7 Phase4：analysis 桥接轻量测试（在 rental_app 下: python test_analysis_bridge.py）
from __future__ import annotations

from unittest.mock import patch

from data.pipeline.analysis_bridge import (
    analyze_multi_source_listings,
    listing_schema_dict_to_batch_property,
    listings_dicts_to_batch_properties,
    listings_to_batch_analysis_payload,
    run_multi_source_analysis,
)
from data.pipeline.multi_source_pipeline import run_multi_source_pipeline


def test_listing_schema_dict_to_batch_property_maps_rent():
    row = {
        "source": "rightmove",
        "rent_pcm": 1500.0,
        "bedrooms": 2,
        "postcode": "E1 6AN",
        "bills_included": True,
    }
    p = listing_schema_dict_to_batch_property(row)
    assert p.get("rent") == 1500.0
    assert p.get("bedrooms") == 2
    assert "E1" in (p.get("postcode") or "")


def test_listings_dicts_to_batch_properties_skips_empty_payload():
    rows = [{"source": "x"}, {"rent_pcm": 800.0, "postcode": "SW1A 1AA"}]
    props, errs = listings_dicts_to_batch_properties(rows)
    assert len(props) == 1
    assert props[0].get("rent") == 800.0
    assert len(errs) >= 1


def test_listings_to_batch_analysis_payload_alias():
    rows = [{"rent_pcm": 1000.0, "bedrooms": 1}]
    assert len(listings_to_batch_analysis_payload(rows)) == 1


def test_analyze_multi_source_listings_empty():
    r = analyze_multi_source_listings([])
    assert r["success"] is False
    assert r["analyze_envelope"] is None
    assert r["properties_built_count"] == 0


def test_run_multi_source_analysis_return_shape_mocked():
    fake_pl = {
        "success": True,
        "sources_run": ["rightmove"],
        "per_source_stats": {},
        "errors": [],
        "total_raw_count": 1,
        "total_normalized_count": 1,
        "total_normalization_skipped": 0,
        "total_saved": 0,
        "total_updated": 0,
        "total_skipped": 0,
        "aggregated_unique_count": 1,
        "aggregated_listings_sample": [],
        "aggregated_listings": [
            {"source": "rightmove", "rent_pcm": 1200.0, "bedrooms": 2, "postcode": "E1 1AA"},
        ],
    }
    fake_env = {
        "success": True,
        "data": {
            "results": [{"index": 0, "success": True, "data": {"score": 7}}],
            "comparison_summary": "ok",
            "top_recommendation": {"top1": None, "top3": [], "sorted_indices_by_score": [0]},
            "top_1_recommendation": None,
        },
        "meta": {"batch_summary": {"requested": 1, "succeeded": 1, "failed": 0}},
        "error": None,
    }
    with patch(
        "data.pipeline.analysis_bridge.run_multi_source_pipeline",
        return_value=fake_pl,
    ):
        with patch(
            "data.pipeline.analysis_bridge.analyze_batch_request_body",
            return_value=fake_env,
        ):
            out = run_multi_source_analysis(sources=["rightmove"], query={}, limit_per_source=1, persist=False)
    assert out["success"] is True
    assert out["sources_run"] == ["rightmove"]
    assert out["total_analyzed_count"] == 1
    assert out["sample_analyzed_listing"] is not None
    assert "pipeline" in out and "aggregated_listings" not in out["pipeline"]


def test_include_aggregated_listings_in_pipeline():
    r = run_multi_source_pipeline(
        sources=["rightmove", "zoopla"],
        query={"search_url": ""},
        limit_per_source=1,
        persist=False,
        include_aggregated_listings=True,
    )
    assert "aggregated_listings" in r
    assert isinstance(r["aggregated_listings"], list)


if __name__ == "__main__":
    test_listing_schema_dict_to_batch_property_maps_rent()
    test_listings_dicts_to_batch_properties_skips_empty_payload()
    test_listings_to_batch_analysis_payload_alias()
    test_analyze_multi_source_listings_empty()
    test_run_multi_source_analysis_return_shape_mocked()
    test_include_aggregated_listings_in_pipeline()
    print("test_analysis_bridge: all ok")
