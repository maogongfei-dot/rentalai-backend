# P5 Phase3 + P7 Phase5: Agent 调度 — intent → 真实多平台抓取 + analyze-batch
from __future__ import annotations

from typing import Any

from web_ui.real_analysis_service import run_real_listings_analysis
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
) -> tuple[dict[str, Any] | None, str | None, dict[str, Any]]:
    """
    **Continue to Analysis**：本地 Playwright 多平台抓取 + `analyze_batch_request_body`。
    与 P4 **Batch results** 使用同一封套（`p2_batch_last`）。

    `use_local` / `api_base_url` 保留签名以兼容调用方；本路径始终进程内执行（与 P2 HTTP batch 无关）。

    Returns:
        (batch_envelope_dict, transport_error_if_exception, request_payload)
    """
    _ = (use_local, api_base_url)  # 保留参数：与 app_web 兼容；Agent 不走 HTTP batch

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
