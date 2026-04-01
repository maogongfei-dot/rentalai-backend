"""
Phase 5 Round3 Step3 — Build minimal history rows and append (best-effort; never raises to callers).

* ``userId``: explicit from request, else ``\"guest\"`` (stable server-side bucket).
* Types: ``property`` | ``contract`` (align with frontend unified history vocabulary).
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from .history_repository import HistoryRepository

logger = logging.getLogger("rentalai.persistence.history")

_REPO = HistoryRepository()

_MAX_SNAPSHOT_CHARS = 12000


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _trim_snapshot(obj: Any) -> Any:
    try:
        import json

        s = json.dumps(obj, ensure_ascii=False, default=str)
        if len(s) <= _MAX_SNAPSHOT_CHARS:
            return obj
        return {"_truncated": True, "preview": s[:_MAX_SNAPSHOT_CHARS] + "…"}
    except (TypeError, ValueError):
        return {"_error": "unserializable_snapshot"}


def resolve_history_user_id(body: Any) -> str:
    """Optional ``userId`` / ``user_id`` on JSON body; otherwise ``guest``."""
    if not isinstance(body, dict):
        return "guest"
    uid = body.get("userId")
    if uid is None:
        uid = body.get("user_id")
    s = str(uid or "").strip()
    if not s:
        return "guest"
    return s[:128]


def append_property_analysis_record(user_id: str, orchestrator_out: dict[str, Any]) -> None:
    """Persist one row after successful ``run_housing_ai_query`` (``success`` true)."""
    if not isinstance(orchestrator_out, dict) or not orchestrator_out.get("success"):
        return
    uid = str(user_id or "").strip() or "guest"
    ut = str(orchestrator_out.get("user_text") or "").strip()
    title = (ut[:120] + "…") if len(ut) > 120 else (ut or "Property analysis")
    nf = orchestrator_out.get("normalized_filters") if isinstance(orchestrator_out.get("normalized_filters"), dict) else {}
    ms = orchestrator_out.get("market_summary") if isinstance(orchestrator_out.get("market_summary"), dict) else {}
    ranked = orchestrator_out.get("top_deals") if isinstance(orchestrator_out.get("top_deals"), dict) else {}
    deals = ranked.get("top_deals") if isinstance(ranked.get("top_deals"), list) else []
    errors = orchestrator_out.get("errors") if isinstance(orchestrator_out.get("errors"), dict) else {}
    summary: dict[str, Any] = {
        "kind": "property",
        "user_text_preview": ut[:500],
        "location": nf.get("location") or nf.get("postcode") or nf.get("area"),
        "market_summary_title": ms.get("summary_title"),
        "top_deal_count": len(deals),
        "error_keys": sorted(errors.keys()) if errors else [],
    }
    result_snapshot: dict[str, Any] = {
        "message": orchestrator_out.get("message"),
        "parsed_intent": (orchestrator_out.get("parsed_query") or {}).get("intent")
        if isinstance(orchestrator_out.get("parsed_query"), dict)
        else None,
    }
    record = {
        "record_id": uuid.uuid4().hex,
        "userId": uid,
        "type": "property",
        "title": title,
        "created_at": _utc_now_iso(),
        "summary": summary,
        "result_snapshot": _trim_snapshot(result_snapshot),
    }
    _REPO.append_record(record)


def append_contract_analysis_record(
    user_id: str,
    *,
    engine: str,
    ui_payload: dict[str, Any],
) -> None:
    """Persist after ``ok: True`` contract analysis (``build_contract_analysis_ui_payload`` result)."""
    if not isinstance(ui_payload, dict):
        return
    uid = str(user_id or "").strip() or "guest"
    sv = ui_payload.get("summary_view") if isinstance(ui_payload.get("summary_view"), dict) else {}
    oc = str(sv.get("overall_conclusion") or "").strip()
    title = (oc[:120] + "…") if len(oc) > 120 else (oc or "Contract analysis")
    if title == "Contract analysis":
        kr = str(sv.get("key_risk_summary") or "").strip()
        if kr:
            title = (kr[:120] + "…") if len(kr) > 120 else kr
    summary: dict[str, Any] = {
        "kind": "contract",
        "engine": engine,
        "overall_conclusion_preview": oc[:800],
        "key_risk_preview": str(sv.get("key_risk_summary") or "")[:800],
    }
    result_snapshot = _trim_snapshot({"summary_view": sv})
    record = {
        "record_id": uuid.uuid4().hex,
        "userId": uid,
        "type": "contract",
        "title": title,
        "created_at": _utc_now_iso(),
        "summary": summary,
        "result_snapshot": result_snapshot,
    }
    _REPO.append_record(record)


def try_append_property(body: dict[str, Any], orchestrator_out: dict[str, Any]) -> None:
    try:
        append_property_analysis_record(resolve_history_user_id(body), orchestrator_out)
    except Exception:
        logger.exception("append_property_analysis_record failed")


def try_append_contract(user_id: str, engine: str, ui_payload: dict[str, Any]) -> None:
    try:
        append_contract_analysis_record(user_id, engine=engine, ui_payload=ui_payload)
    except Exception:
        logger.exception("append_contract_analysis_record failed")
