"""Chat router (Phase 1 skeleton)."""

from __future__ import annotations

from .followup_builder import build_chat_followup_bundle
from .comparison import (
    build_comparison_response_text,
    extract_property_comparison_inputs,
    run_basic_property_comparison,
)
from .intent_rules import classify_intent
from .property_input import (
    build_property_reference,
    parse_property_input,
)
from .analysis_route import (
    build_analysis_entry_result,
    decide_analysis_route,
)
from .location import build_uk_location_context
from .presentation import build_chat_display_bundle
from .preference_detection import detect_user_preferences
from .query_scope import classify_query_scope
from .router import handle_chat_request

__all__ = [
    "build_analysis_entry_result",
    "build_chat_followup_bundle",
    "build_comparison_response_text",
    "build_property_reference",
    "classify_intent",
    "decide_analysis_route",
    "build_chat_display_bundle",
    "build_uk_location_context",
    "classify_query_scope",
    "detect_user_preferences",
    "extract_property_comparison_inputs",
    "handle_chat_request",
    "parse_property_input",
    "run_basic_property_comparison",
]
