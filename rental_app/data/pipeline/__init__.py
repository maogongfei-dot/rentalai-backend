# P6 Phase4+：数据层编排（抓取闭环等）
from .analysis_bridge import (
    analyze_multi_source_listings,
    fetch_multi_source_listings,
    listing_schema_dict_to_batch_property,
    listings_dicts_to_batch_properties,
    listings_to_batch_analysis_payload,
    run_multi_source_analysis,
)
from .multi_source_pipeline import (
    PIPELINE_REGISTRY,
    dedupe_normalized_listings,
    run_multi_source_normalization_pipeline,
    run_multi_source_pipeline,
    run_source_pipeline,
)
from .rightmove_pipeline import (
    run_rightmove_normalization_pipeline,
    run_rightmove_pipeline,
    scrape_and_normalize_rightmove,
)
from .zoopla_pipeline import (
    run_zoopla_normalization_pipeline,
    run_zoopla_pipeline,
    scrape_and_normalize_zoopla,
)

__all__ = [
    "analyze_multi_source_listings",
    "fetch_multi_source_listings",
    "listing_schema_dict_to_batch_property",
    "listings_dicts_to_batch_properties",
    "listings_to_batch_analysis_payload",
    "PIPELINE_REGISTRY",
    "dedupe_normalized_listings",
    "run_multi_source_analysis",
    "run_multi_source_normalization_pipeline",
    "run_multi_source_pipeline",
    "run_rightmove_normalization_pipeline",
    "run_rightmove_pipeline",
    "run_source_pipeline",
    "run_zoopla_normalization_pipeline",
    "run_zoopla_pipeline",
    "scrape_and_normalize_rightmove",
    "scrape_and_normalize_zoopla",
]
