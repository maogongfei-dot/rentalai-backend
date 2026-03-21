# P7 Phase5：前端统一入口 — 多平台抓取 + analyze-batch（不改 pipeline / 评分核心）
from __future__ import annotations

import time
from typing import Any

from api_analysis import BATCH_API_VERSION, BATCH_ENDPOINT, build_meta
from web_ui.intent_to_payload import build_batch_property_from_intent
from web_ui.rental_intent import AgentRentalRequest
from web_ui.rental_intent_parser import intent_has_key_signals


def _float_opt(v: Any) -> float | None:
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip()
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _int_opt(v: Any) -> int | None:
    f = _float_opt(v)
    if f is None:
        return None
    try:
        return int(f)
    except (TypeError, ValueError):
        return None


def build_scenario_property_for_request(
    intent: AgentRentalRequest | None,
    form_raw: dict[str, Any] | None,
) -> dict[str, Any]:
    """
    写入 `p2_batch_last_request` 的「场景」行：优先 Agent intent，否则 Property details 表单。
    仅用于 UI 摘要与 insight，与真实抓取 URL（各平台默认 London）独立。
    """
    if intent is not None and (
        intent_has_key_signals(intent) or (intent.raw_query or "").strip()
    ):
        return build_batch_property_from_intent(intent)
    raw = form_raw if isinstance(form_raw, dict) else {}
    rent = _float_opt(raw.get("rent")) or 1200.0
    budget = _float_opt(raw.get("budget"))
    if budget is None:
        budget = rent * 1.15
    if budget < rent:
        budget = rent + 1.0
    commute = _int_opt(raw.get("commute_minutes"))
    if commute is None:
        commute = 30
    bedrooms = _int_opt(raw.get("bedrooms"))
    if bedrooms is None:
        bedrooms = 2
    prop: dict[str, Any] = {
        "rent": rent,
        "budget": float(budget),
        "commute_minutes": commute,
        "bedrooms": bedrooms,
        "bills_included": bool(raw.get("bills_included", False)),
    }
    area = (raw.get("area") or "").strip()
    if area:
        prop["area"] = area
    pc = (raw.get("postcode") or "").strip()
    if pc:
        prop["postcode"] = pc
    tp = (raw.get("target_postcode") or "").strip()
    if tp:
        prop["target_postcode"] = tp
    dist = _float_opt(raw.get("distance"))
    if dist is not None:
        prop["distance"] = dist
    return prop


def _resolve_budget_target_postcode(
    intent: AgentRentalRequest | None,
    form_raw: dict[str, Any] | None,
) -> tuple[float | None, str | None]:
    p = build_scenario_property_for_request(intent, form_raw)
    b = _float_opt(p.get("budget"))
    tp = p.get("target_postcode")
    if isinstance(tp, str) and tp.strip():
        return b, tp.strip()
    return b, None


def _attach_p7_meta(envelope: dict[str, Any], debug: dict[str, Any]) -> dict[str, Any]:
    out = dict(envelope)
    meta = dict(out.get("meta") or {})
    meta["p7_real_listings"] = debug
    out["meta"] = meta
    return out


def _synthetic_failure_envelope(message: str, debug: dict[str, Any]) -> dict[str, Any]:
    base = build_meta(BATCH_ENDPOINT, api_version=BATCH_API_VERSION)
    base["p7_real_listings"] = debug
    return {
        "success": False,
        "data": None,
        "error": {"message": message, "type": "p7_bridge"},
        "meta": base,
    }


def run_real_listings_analysis(
    *,
    intent: AgentRentalRequest | None = None,
    form_raw: dict[str, Any] | None = None,
    sources: list[str] | None = None,
    limit_per_source: int = 10,
    persist: bool = True,
    storage_path: str | None = None,
    headless: bool = True,
) -> tuple[dict[str, Any], str | None, dict[str, Any]]:
    """
    调用 `run_multi_source_analysis`，并把结果整理成与 **POST /analyze-batch** 一致的封套
    （供 `st.session_state['p2_batch_last']` 与 P4 结果区复用）。

    Returns:
        (envelope, optional_transport_error, request_payload_for_session)
    """
    t0 = time.perf_counter()
    scenario = build_scenario_property_for_request(intent, form_raw)
    budget, target_pc = _resolve_budget_target_postcode(intent, form_raw)
    query: dict[str, Any] = {"headless": bool(headless)}

    request_payload: dict[str, Any] = {
        "properties": [scenario],
        "_p7_multi_source": True,
    }

    try:
        from data.pipeline.analysis_bridge import run_multi_source_analysis

        msa = run_multi_source_analysis(
            sources=sources,
            query=query,
            limit_per_source=limit_per_source,
            persist=persist,
            storage_path=storage_path,
            budget=budget,
            target_postcode=target_pc,
        )
    except Exception as e:  # noqa: BLE001
        elapsed = round(time.perf_counter() - t0, 2)
        dbg = {
            "sources_run": [],
            "total_raw_count": 0,
            "aggregated_unique_count": 0,
            "total_analyzed_count": 0,
            "seconds": elapsed,
            "exception": "%s: %s" % (type(e).__name__, e),
        }
        request_payload["_p7_debug"] = dbg
        syn = _synthetic_failure_envelope(
            "Real listings run failed: %s" % e,
            dbg,
        )
        return syn, str(e), request_payload

    elapsed = round(time.perf_counter() - t0, 2)
    dbg = {
        "sources_run": msa.get("sources_run") or [],
        "total_raw_count": msa.get("total_raw_count"),
        "aggregated_unique_count": msa.get("aggregated_unique_count"),
        "total_normalized_count": msa.get("total_normalized_count"),
        "total_analyzed_count": msa.get("total_analyzed_count"),
        "properties_built_count": msa.get("properties_built_count"),
        "pipeline_success": msa.get("pipeline_success"),
        "seconds": elapsed,
    }
    request_payload["_p7_debug"] = dbg

    env = msa.get("analysis_envelope")
    if isinstance(env, dict) and env:
        return _attach_p7_meta(env, dbg), None, request_payload

    agg = int(msa.get("aggregated_unique_count") or 0)
    if agg == 0:
        msg = "No listings found, try adjusting your criteria"
    else:
        msg = (
            "No listings could be analyzed after scraping. "
            "Try different criteria or check pipeline logs."
        )
    syn = _synthetic_failure_envelope(msg, dbg)
    meta = dict(syn.get("meta") or {})
    meta["p7_errors"] = msa.get("errors") or []
    syn["meta"] = meta
    return syn, None, request_payload
