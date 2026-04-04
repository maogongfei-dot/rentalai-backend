"""
Phase 5 Round3 Step3 — Build minimal history rows and append (best-effort; never raises to callers).

* ``userId``: 由 HTTP 层 ``auth_http_helpers.resolve_history_write_user_id`` 解析（guest / token 用户）。
* HTTP 层写入前须通过 ``resolve_history_write_user_id``（非 guest 须 Bearer）。
* Types: ``property`` | ``contract`` (align with frontend unified history vocabulary).

Phase 5 Round6 Step3 — 统一入口 :func:`persist_analysis_history`；房源 / 合同分析共用同一套落库形状。

Phase 5 Round6 Step5 — 与 ``resolve_history_write_user_id`` + 各分析路由的 **try_persist_*** 组成「受保护写入」收尾；未做 JWT/过期/云端删除（见 ``persistence/README.md``）。
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


def persist_analysis_history(
    user_id: str,
    *,
    record_type: str,
    title: str,
    short_label: str | None = None,
    summary: dict[str, Any],
    result_snapshot: Any,
    created_at_iso: str | None = None,
    input_text: str | None = None,
) -> None:
    """
    统一写入一条分析历史（房源 / 合同共用）。

    最少字段：``type``、``title``、``created_at``、``summary``、``result`` / ``result_snapshot``、``userId``（记录顶层）；
    ``summary`` 内带 ``identity_user_id``（与 HTTP 层解析一致）、``kind`` 与可选 ``short_label``。
    """
    uid = str(user_id or "").strip() or "guest"
    rt = str(record_type or "").strip().lower()
    if rt not in ("property", "contract"):
        rt = "property"
    t = str(title or "").strip() or ("Property analysis" if rt == "property" else "Contract analysis")
    if len(t) > 200:
        t = t[:197] + "…"
    summ = dict(summary) if isinstance(summary, dict) else {}
    summ.setdefault("identity_user_id", uid)
    summ.setdefault("kind", rt)
    sl = str(short_label or "").strip()
    if sl:
        summ["short_label"] = sl[:200]
    inp = (input_text or "").strip()
    if inp and "input_preview" not in summ:
        summ["input_preview"] = inp[:2000]
    trimmed = _trim_snapshot(result_snapshot)
    record = {
        "record_id": uuid.uuid4().hex,
        "userId": uid,
        "user_id": uid,
        "type": rt,
        "title": t,
        "created_at": created_at_iso or _utc_now_iso(),
        "input": inp[:8000] if inp else "",
        "summary": summ,
        "result": trimmed,
        "result_snapshot": trimmed,
    }
    _REPO.append_record(record)


# Alias for naming preference (Round6 Step3)
save_analysis_snapshot = persist_analysis_history


def save_analysis(payload: dict[str, Any]) -> None:
    """Explicit cloud save (JSON file via :class:`HistoryRepository`).

    Expected keys: ``user_id`` (or ``userId``), ``type`` (``property`` | ``contract``), ``result`` (full API result dict).
    Optional: ``input``, ``summary``, ``created_at`` (reserved for callers; persistence uses ``persist_*`` shapes).
    """
    uid = str(payload.get("user_id") or payload.get("userId") or "").strip() or "guest"
    rt = str(payload.get("type") or "property").strip().lower()
    res = payload.get("result")
    if rt == "contract":
        if not isinstance(res, dict):
            return
        persist_contract_analysis_snapshot(uid, "contract_analysis_v1", res)
        return
    if isinstance(res, dict) and res.get("success"):
        persist_property_analysis_snapshot(uid, res)


def persist_property_analysis_snapshot(user_id: str, orchestrator_out: dict[str, Any]) -> None:
    """房源分析成功后：从 ``run_housing_ai_query`` 结果构建快照并 :func:`persist_analysis_history`。"""
    if not isinstance(orchestrator_out, dict) or not orchestrator_out.get("success"):
        return
    ut = str(orchestrator_out.get("user_text") or "").strip()
    title = (ut[:120] + "…") if len(ut) > 120 else (ut or "Property analysis")
    nf = orchestrator_out.get("normalized_filters") if isinstance(orchestrator_out.get("normalized_filters"), dict) else {}
    ms = orchestrator_out.get("market_summary") if isinstance(orchestrator_out.get("market_summary"), dict) else {}
    ranked = orchestrator_out.get("top_deals") if isinstance(orchestrator_out.get("top_deals"), dict) else {}
    deals = ranked.get("top_deals") if isinstance(ranked.get("top_deals"), list) else []
    errors = orchestrator_out.get("errors") if isinstance(orchestrator_out.get("errors"), dict) else {}
    loc = nf.get("location") or nf.get("postcode") or nf.get("area")
    short_label: str | None = None
    if ms.get("summary_title"):
        short_label = str(ms.get("summary_title"))[:160]
    elif loc:
        short_label = str(loc)[:160]
    summary: dict[str, Any] = {
        "kind": "property",
        "user_text_preview": ut[:500],
        "location": loc,
        "market_summary_title": ms.get("summary_title"),
        "top_deal_count": len(deals),
        "error_keys": sorted(errors.keys()) if errors else [],
    }
    persist_analysis_history(
        user_id,
        record_type="property",
        title=title,
        short_label=short_label,
        summary=summary,
        result_snapshot=orchestrator_out,
        input_text=ut,
    )


def persist_contract_analysis_snapshot(user_id: str, engine: str, ui_payload: dict[str, Any]) -> None:
    """合同分析成功后：从 UI payload 构建快照并 :func:`persist_analysis_history`。"""
    if not isinstance(ui_payload, dict):
        return
    sv = ui_payload.get("summary_view") if isinstance(ui_payload.get("summary_view"), dict) else {}
    oc = str(sv.get("overall_conclusion") or "").strip()
    title = (oc[:120] + "…") if len(oc) > 120 else (oc or "Contract analysis")
    if title == "Contract analysis":
        kr = str(sv.get("key_risk_summary") or "").strip()
        if kr:
            title = (kr[:120] + "…") if len(kr) > 120 else kr
    short_label = str(engine or "").strip()[:80] or None
    summary: dict[str, Any] = {
        "kind": "contract",
        "engine": engine,
        "overall_conclusion_preview": oc[:800],
        "key_risk_preview": str(sv.get("key_risk_summary") or "")[:800],
    }
    raw = ui_payload.get("raw_analysis") if isinstance(ui_payload.get("raw_analysis"), dict) else {}
    ar = raw.get("analysis_result") if isinstance(raw.get("analysis_result"), dict) else {}
    cin = str(ar.get("contract_text") or ar.get("source_text") or ar.get("text") or "")[:8000]
    persist_analysis_history(
        user_id,
        record_type="contract",
        title=title,
        short_label=short_label,
        summary=summary,
        result_snapshot=ui_payload,
        input_text=cin or oc[:2000],
    )


def append_property_analysis_record(user_id: str, orchestrator_out: dict[str, Any]) -> None:
    """Persist one row after successful ``run_housing_ai_query`` (``success`` true)."""
    persist_property_analysis_snapshot(user_id, orchestrator_out)


def append_contract_analysis_record(
    user_id: str,
    *,
    engine: str,
    ui_payload: dict[str, Any],
) -> None:
    """Persist after ``ok: True`` contract analysis (``build_contract_analysis_ui_payload`` result)."""
    persist_contract_analysis_snapshot(user_id, engine, ui_payload)


def try_persist_property_analysis_snapshot(user_id: str, orchestrator_out: dict[str, Any]) -> None:
    try:
        persist_property_analysis_snapshot(user_id, orchestrator_out)
    except Exception:
        logger.exception("persist_property_analysis_snapshot failed")


def try_persist_contract_analysis_snapshot(user_id: str, engine: str, ui_payload: dict[str, Any]) -> None:
    try:
        persist_contract_analysis_snapshot(user_id, engine, ui_payload)
    except Exception:
        logger.exception("persist_contract_analysis_snapshot failed")


def try_append_property(body: dict[str, Any], orchestrator_out: dict[str, Any]) -> None:
    try:
        append_property_analysis_record(resolve_history_user_id(body), orchestrator_out)
    except Exception:
        logger.exception("append_property_analysis_record failed")


def try_append_contract(user_id: str, engine: str, ui_payload: dict[str, Any]) -> None:
    """Best-effort contract append（与 :func:`try_persist_contract_analysis_snapshot` 等价）。"""
    try_persist_contract_analysis_snapshot(user_id, engine, ui_payload)
