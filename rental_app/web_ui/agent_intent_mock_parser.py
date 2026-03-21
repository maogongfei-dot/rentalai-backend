# P5 Phase1 兼容名：请优先使用 `web_ui.rental_intent_parser.parse_rental_intent`
from __future__ import annotations

from web_ui.rental_intent import AgentRentalRequest
from web_ui.rental_intent_parser import parse_rental_intent


def parse_rental_intent_mock(text: str) -> AgentRentalRequest:
    """与 `parse_rental_intent` 相同；保留别名以免旧 import 断裂。"""
    return parse_rental_intent(text)
