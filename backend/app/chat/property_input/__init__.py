"""Phase 1 Part 6: unified property input detection (links, postcodes, addresses)."""

from __future__ import annotations

from .parser import (
    build_property_reference,
    parse_property_input,
    property_input_voice_line,
)

__all__ = [
    "build_property_reference",
    "parse_property_input",
    "property_input_voice_line",
]
