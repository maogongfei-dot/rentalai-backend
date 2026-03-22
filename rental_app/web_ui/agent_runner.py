# P5 Phase3 + P7 Phase5: Agent 调度 — intent → 真实多平台抓取 + analyze-batch
from __future__ import annotations

from typing import Any, Callable

from web_ui.real_analysis_service import (
    run_real_listings_analysis,
    run_real_listings_analysis_async,
)
from web_ui.rental_intent import AgentRentalRequest
from web_ui.rental_intent_parser import intent_has_key_signals


def run_agent_intent_analysis(
    intent: AgentRentalRequest,
    *,
    use_local: bool,
    api_base_url: str,
    limit_per_source: int = 10,
    headless: bool = True,
    persist_listings: bool = True,
    async_mode: bool = False,
    on_status: Callable[[str, str], None] | None = None,
    auth_token: str | None = None,
) -> tuple[dict[str, Any] | None, str | None, dict[str, Any]]:
    """
    **Continue to Analysis**：多平台抓取 + `analyze_batch_request_body`。
    与 P4 **Batch results** 使用同一封套（`p2_batch_last`）。

    When *async_mode* is True, delegates to the FastAPI backend via
    ``POST /tasks`` + polling, using the same pattern as the batch button.

    Returns:
        (batch_envelope_dict, transport_error_if_exception, request_payload)
    """
    if async_mode:
        return run_real_listings_analysis_async(
            api_base_url=api_base_url,
            intent=intent,
            form_raw=None,
            limit_per_source=limit_per_source,
            headless=headless,
            persist=persist_listings,
            on_status=on_status,
            auth_token=auth_token,
        )

    env, err, payload = run_real_listings_analysis(
        intent=intent,
        form_raw=None,
        sources=None,
        limit_per_source=limit_per_source,
        persist=persist_listings,
        headless=headless,
    )
    return env, err, payload


def agent_intent_sparse_warning(intent: AgentRentalRequest) -> str | None:
    """几乎无结构化字段时的轻量提示（仍允许跑抓取 + batch + 默认值）。"""
    if not (intent.raw_query or "").strip():
        return None
    if intent_has_key_signals(intent):
        return None
    return (
        "Few fields were parsed — the real run still uses **safe numeric defaults** "
        "for budget/commute/bedrooms when mapping to the engine. Refine wording or edit the form."
    )
