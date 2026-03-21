# P6 Phase4+：数据层编排（抓取闭环等）
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
    "PIPELINE_REGISTRY",
    "dedupe_normalized_listings",
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
