# P5 Phase3: Agent 调度 — 自然语言 intent → /analyze-batch（单条 properties），无 LLM
from __future__ import annotations

from typing import Any

from web_ui.intent_to_payload import build_batch_request_from_intent
from web_ui.rental_intent import AgentRentalRequest
from web_ui.rental_intent_parser import intent_has_key_signals


def run_agent_intent_analysis(
    intent: AgentRentalRequest,
    *,
    use_local: bool,
    api_base_url: str,
) -> tuple[dict[str, Any] | None, str | None, dict[str, Any]]:
    """
    默认走 **analyze-batch**（单条需求），与现有 batch 结果区、Top picks、筛选一致。

    Returns:
        (response_dict, transport_error_message, request_payload)
    """
    payload = build_batch_request_from_intent(intent)

    if use_local:
        try:
            from api_analysis import analyze_batch_request_body

            out = analyze_batch_request_body(payload)
            if not isinstance(out, dict):
                return None, "Invalid batch response type", payload
            return out, None, payload
        except Exception as e:
            return None, str(e), payload

    import requests

    url = "%s/analyze-batch" % (api_base_url or "").rstrip("/")
    try:
        resp = requests.post(url, json=payload, timeout=180)
        resp.raise_for_status()
        data = resp.json()
        if not isinstance(data, dict):
            return None, "API returned non-JSON object", payload
        return data, None, payload
    except Exception as e:
        return None, "Batch request failed: %s" % (e,), payload


def agent_intent_sparse_warning(intent: AgentRentalRequest) -> str | None:
    """几乎无结构化字段时的轻量提示（仍允许跑 batch + 默认值）。"""
    if not (intent.raw_query or "").strip():
        return None
    if intent_has_key_signals(intent):
        return None
    return (
        "Few fields were parsed — batch run uses **numeric defaults** "
        "(rent/budget/commute/bedrooms). Refine wording or edit the form below."
    )
