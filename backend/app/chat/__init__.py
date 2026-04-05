"""Chat router (Phase 1 skeleton)."""

from __future__ import annotations

from .followup_builder import build_chat_followup_bundle
from .intent_rules import classify_intent
from .preference_detection import detect_user_preferences
from .router import handle_chat_request

__all__ = [
    "build_chat_followup_bundle",
    "classify_intent",
    "detect_user_preferences",
    "handle_chat_request",
]
