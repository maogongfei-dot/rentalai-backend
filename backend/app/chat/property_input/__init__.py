"""Phase 1 Part 6: unified property input detection (links, postcodes, addresses)."""

from __future__ import annotations

from .parser import (
    assess_input_completeness,
    build_property_reference,
    parse_property_input,
    property_input_voice_line,
)

__all__ = [
    "assess_input_completeness",
    "build_property_reference",
    "parse_property_input",
    "property_input_voice_line",
]
