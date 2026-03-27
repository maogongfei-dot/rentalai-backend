# Phase C5：统一 LLM 接口层 — 当前实现委托规则引擎；未来可替换为 OpenAI / 本地模型。
from __future__ import annotations

import os
from typing import Any

from rental_decision_v2 import build_decision_v2
from rental_explain_v2 import build_explain_v2
from rental_query_parser import parse_user_query

# 模式开关：rule（默认）| llm（未来；当前仍 fallback 到规则）
LLM_MODE = (os.environ.get("RENTALAI_LLM_MODE") or "rule").strip().lower()

# 未来接模型时的 prompt 占位（本阶段不调用任何 API）
PROMPT_TEMPLATES: dict[str, str] = {
    "parse_query": (
        "Extract structured rental search requirements from the user's message. "
        "Return fields such as budget, location, bedrooms, bills, commute, and preferences as JSON."
    ),
    "explain": (
        "Given a listing and the user's structured requirements, explain match quality, "
        "trade-offs, and what to verify next. Be concise."
    ),
    "decision": (
        "Given scores, explain_v2, and risks, output a recommendation label (e.g. RECOMMENDED / CAUTION / NOT_RECOMMENDED) "
        "and a short rationale."
    ),
}

_logged_mode = False


def _log_mode_once() -> None:
    global _logged_mode
    if _logged_mode:
        return
    _logged_mode = True
    print("[LLM_ADAPTER] mode=%s (RENTALAI_LLM_MODE)" % LLM_MODE)


def llm_parse_query(raw_user_query: str) -> dict[str, Any]:
    """
    自然语言 → structured_query。
    rule：parse_user_query；llm：预留，当前 fallback 到规则。
    """
    _log_mode_once()
    if LLM_MODE == "llm":
        # TODO: 调用 OpenAI / 本地模型，解析为与 parse_user_query 同结构的 dict
        return parse_user_query(raw_user_query)
    return parse_user_query(raw_user_query)


def llm_generate_explain(
    house: dict[str, Any],
    structured_query: dict[str, Any],
    *,
    base_scores: dict[str, Any] | None = None,
    legacy_explain: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    单条房源 + 用户需求 → explain_v2 核心字段（不含 match_summary）。
    rule：build_explain_v2；llm：预留，当前 fallback。
    """
    _log_mode_once()
    if legacy_explain is None:
        from ai_recommendation_bridge import _build_legacy_explain_block

        legacy_explain = _build_legacy_explain_block(house)
    if LLM_MODE == "llm":
        # TODO: 传入 PROMPT_TEMPLATES["explain"] + house + structured_query，解析为与 build_explain_v2 同结构 dict
        pass
    return build_explain_v2(
        house,
        structured_query,
        base_scores=base_scores,
        legacy_explain=legacy_explain,
    )


def llm_generate_decision(
    house: dict[str, Any],
    structured_query: dict[str, Any],
    explain_v2: dict[str, Any],
    *,
    base_scores: dict[str, Any] | None = None,
    legacy_explain: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    单条房源 + structured_query + explain_v2 → decision_v2。
    rule：build_decision_v2；llm：预留，当前 fallback。
    legacy_explain：提供 risks / why_not 供规则层使用。
    """
    _log_mode_once()
    if legacy_explain is None:
        from ai_recommendation_bridge import _build_legacy_explain_block

        legacy_explain = _build_legacy_explain_block(house)
    risks = legacy_explain.get("risks") if isinstance(legacy_explain, dict) else None
    why_not = legacy_explain.get("why_not") if isinstance(legacy_explain, dict) else None
    if LLM_MODE == "llm":
        # TODO: 传入 PROMPT_TEMPLATES["decision"] + 上下文，映射为 build_decision_v2 兼容结构
        pass
    return build_decision_v2(
        house,
        structured_query,
        explain_v2,
        base_scores=base_scores,
        risks=risks,
        why_not=why_not,
    )
