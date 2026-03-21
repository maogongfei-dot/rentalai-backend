# P7 Phase5：real_analysis_service 轻量测试（在 rental_app 下: python test_real_analysis_service.py）
from __future__ import annotations

from unittest.mock import patch

from web_ui.real_analysis_service import (
    build_scenario_property_for_request,
    run_real_listings_analysis,
)
from web_ui.rental_intent import AgentRentalRequest


def test_build_scenario_from_form():
    raw = {
        "rent": "1100",
        "budget": "1300",
        "commute_minutes": "25",
        "bedrooms": "1",
        "bills_included": True,
        "target_postcode": "E1 6AN",
    }
    p = build_scenario_property_for_request(None, raw)
    assert p.get("budget") == 1300.0
    assert p.get("target_postcode") == "E1 6AN"


def test_run_real_attaches_envelope():
    fake_msa = {
        "success": True,
        "analysis_envelope": {
            "success": True,
            "data": {"results": []},
            "error": None,
            "meta": {"batch_summary": {"requested": 0, "succeeded": 0, "failed": 0}},
        },
        "sources_run": ["rightmove"],
        "total_raw_count": 2,
        "aggregated_unique_count": 2,
        "total_normalized_count": 2,
        "total_analyzed_count": 0,
        "properties_built_count": 0,
        "pipeline_success": True,
        "errors": [],
    }
    with patch(
        "data.pipeline.analysis_bridge.run_multi_source_analysis",
        return_value=fake_msa,
    ):
        env, err, req = run_real_listings_analysis(
            intent=None,
            form_raw={"budget": "1500"},
            limit_per_source=2,
            persist=False,
            headless=True,
        )
    assert err is None
    assert env.get("success") is True
    assert req.get("_p7_multi_source") is True
    assert req["_p7_debug"]["sources_run"] == ["rightmove"]


if __name__ == "__main__":
    test_build_scenario_from_form()
    test_run_real_attaches_envelope()
    print("test_real_analysis_service: all ok")
