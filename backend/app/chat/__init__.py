"""Chat router (Phase 1 skeleton)."""

from __future__ import annotations

from .intent_rules import classify_intent
from .router import handle_chat_request

__all__ = ["classify_intent", "handle_chat_request"]
