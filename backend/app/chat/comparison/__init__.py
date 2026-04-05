"""Phase 1 Part 5: multi-property comparison (rule-based; no scraping)."""

from __future__ import annotations

from .engine import (
    build_comparison_response_text,
    build_property_snapshot_from_side,
    run_basic_property_comparison,
)
from .parser import coerce_comparison_inputs, extract_property_comparison_inputs

__all__ = [
    "build_comparison_response_text",
    "build_property_snapshot_from_side",
    "coerce_comparison_inputs",
    "extract_property_comparison_inputs",
    "run_basic_property_comparison",
]
