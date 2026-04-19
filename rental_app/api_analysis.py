# P2 Phase1–5: API 层 — 标准化封套 + 多接口 + 批量分析与标准推荐输出（仍统一走 run_web_demo_analysis）

from __future__ import annotations

import logging
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from modules.explain import build_explanation_result

_perf_log = logging.getLogger("rentalai.perf")

_BATCH_MAX_ITEMS = int(os.environ.get("RENTALAI_BATCH_MAX", "50"))
_BATCH_WORKERS = int(os.environ.get("RENTALAI_BATCH_WORKERS", "4"))

# ---------- 标准元信息与错误类型 ----------

ERR_VALIDATION = "validation_error"
ERR_BAD_TYPE = "type_error"
ERR_ENGINE = "engine_error"
ERR_INTERNAL = "internal_error"

# API 响应版本（按端点区分）
DEFAULT_API_VERSION = "P2-Phase3"
BATCH_API_VERSION = "P2-Phase5"
BATCH_ENDPOINT = "/analyze-batch"

# 标准请求字段（额外 target_postcode 兼容 Web UI）
STANDARD_INPUT_KEYS = frozenset(
    {
        "rent",
        "bills_included",
        "commute_minutes",
        "bedrooms",
        "budget",
        "postcode",
        "area",
        "distance",
        "target_postcode",
    }
)


def build_meta(endpoint: str, *, api_version: str | None = None) -> dict:
    """统一 meta；未指定 version 时默认 Phase3。"""
    return {
        "source": "RentalAI API",
        "version": api_version or DEFAULT_API_VERSION,
        "endpoint": endpoint,
    }


def extract_standard_fields(raw: dict) -> dict:
    """只保留允许字段，忽略未知 key。"""
    return {k: raw[k] for k in raw if k in STANDARD_INPUT_KEYS}


def normalize_api_input(raw: Any) -> tuple[bool, list[str], dict]:
    """
    数字 normalize、bills 布尔化、空串视为未提供（由 web_bridge 兜底）。
    显式提供但无法解析的类型 → 错误列表。
    """
    errors: list[str] = []
    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        return False, ["Request body must be a JSON object"], {}

    out = extract_standard_fields(raw)

    for key in ("rent", "budget", "commute_minutes", "bedrooms"):
        if key not in out:
            continue
        val = out[key]
        if val is None or (isinstance(val, str) and not str(val).strip()):
            out.pop(key, None)
            continue
        try:
            if key in ("commute_minutes", "bedrooms"):
                out[key] = int(float(val))
            else:
                out[key] = float(val)
        except (TypeError, ValueError):
            errors.append("Field '%s' must be numeric when provided" % key)

    if "distance" in out:
        dv = out["distance"]
        if dv is None or (isinstance(dv, str) and not str(dv).strip()):
            out.pop("distance", None)
        else:
            try:
                out["distance"] = float(dv)
            except (TypeError, ValueError):
                errors.append("Field 'distance' must be numeric when provided")

    for sk in ("area", "postcode", "target_postcode"):
        if sk not in out:
            continue
        v = out[sk]
        if v is None:
            continue
        if isinstance(v, str):
            s = v.strip()
            out[sk] = s or None
        else:
            out[sk] = str(v).strip() or None

    if "bills_included" in out:
        b = out["bills_included"]
        if isinstance(b, bool):
            pass
        elif isinstance(b, (int, float)):
            out["bills_included"] = bool(int(b))
        elif isinstance(b, str):
            sl = b.strip().lower()
            if not sl:
                out.pop("bills_included", None)
            else:
                out["bills_included"] = sl in (
                    "yes",
                    "y",
                    "true",
                    "1",
                    "包",
                    "包含",
                )
        elif b is None:
            out.pop("bills_included", None)
        else:
            errors.append(
                "Field 'bills_included' must be boolean, number, or yes/no string"
            )

    if errors:
        return False, errors, {}
    return True, [], out


def call_analysis_engine(input_data: dict) -> dict:
    from web_bridge import run_web_demo_analysis

    return run_web_demo_analysis(input_data)


def normalize_engine_output(engine_result: dict) -> dict:
    """引擎 dict → /analyze 用标准 data 块。"""
    engine_result = engine_result if isinstance(engine_result, dict) else {}
    p = engine_result.get("unified_decision_payload")
    if not isinstance(p, dict):
        p = {}

    status = p.get("status") if isinstance(p.get("status"), dict) else {}

    thx = engine_result.get("top_house_export")
    esum = engine_result.get("explanation_summary") if isinstance(engine_result.get("explanation_summary"), dict) else {}
    expl = engine_result.get("explanation") if isinstance(engine_result.get("explanation"), dict) else {}
    analysis_part = p.get("analysis") if isinstance(p.get("analysis"), dict) else {}

    risks_for_explain: list[Any] = []
    for kr in (esum.get("key_risks"), expl.get("key_risks")):
        if isinstance(kr, list) and kr:
            risks_for_explain = list(kr[:15])
            break
        if kr not in (None, "") and not isinstance(kr, list):
            risks_for_explain = [kr]
            break
    if not risks_for_explain:
        pb = analysis_part.get("primary_blockers")
        if isinstance(pb, list) and pb:
            risks_for_explain = list(pb[:15])

    reasons_for_explain: list[str] = []
    sup = analysis_part.get("supporting_reasons")
    if isinstance(sup, list):
        reasons_for_explain.extend(str(x).strip() for x in sup if str(x).strip())
    for kp in (esum.get("key_positives"), expl.get("key_positives")):
        if not isinstance(kp, list):
            continue
        for x in kp[:10]:
            s = str(x).strip()
            if s:
                reasons_for_explain.append(s)

    analysis_result = {
        "score": engine_result.get("property_score"),
        "risks": risks_for_explain,
        "reasons": reasons_for_explain[:15],
    }
    explain_result = build_explanation_result(analysis_result)

    return {
        "score": engine_result.get("property_score"),
        "decision": p.get("decision") if isinstance(p.get("decision"), dict) else {},
        "analysis": p.get("analysis") if isinstance(p.get("analysis"), dict) else {},
        "user_facing": p.get("user_facing") if isinstance(p.get("user_facing"), dict) else {},
        "references": p.get("references") if isinstance(p.get("references"), dict) else {},
        "trace": p.get("trace") if isinstance(p.get("trace"), dict) else {},
        "status": status,
        "final_recommendation": engine_result.get("final_recommendation") or {},
        "explanation_summary": engine_result.get("explanation_summary") or {},
        "explanation": engine_result.get("explanation") or {},
        "unified_decision": engine_result.get("unified_decision") or {},
        "risk_result": engine_result.get("risk_result")
        if isinstance(engine_result.get("risk_result"), dict)
        else {"status": "placeholder", "message": "No contract risk input"},
        # P4 Phase3: 前端详情页评分明细（引擎已有则透传，缺省为空 dict）
        "top_house_export": thx if isinstance(thx, dict) else {},
        "explain_result": explain_result,
    }


def build_success_response(
    engine_result: dict,
    *,
    endpoint: str = "/analyze",
    api_version: str | None = None,
) -> dict:
    """success=true 的标准封套（全量分析）。"""
    engine_result = engine_result if isinstance(engine_result, dict) else {}
    data = normalize_engine_output(engine_result)
    meta = build_meta(endpoint, api_version=api_version)
    meta["engine_message"] = engine_result.get("message") or ""
    return {
        "success": True,
        "data": data,
        "error": None,
        "meta": meta,
    }


def build_error_response(
    message: str,
    err_type: str,
    details: Any = None,
    *,
    endpoint: str = "/analyze",
    api_version: str | None = None,
) -> dict:
    err_obj: dict[str, Any] = {"message": message, "type": err_type}
    if details is not None:
        err_obj["details"] = details
    return {
        "success": False,
        "data": None,
        "error": err_obj,
        "meta": build_meta(endpoint, api_version=api_version),
    }


def run_standard_pipeline(
    raw_body: Any, endpoint: str
) -> tuple[dict | None, dict | None, dict | None]:
    """
    校验 → normalize_web_form_inputs → run_web_demo_analysis。
    返回 (error_envelope, input_data, engine_out)；成功时 error 为 None。
    """
    try:
        ok, errs, coerced = normalize_api_input(raw_body)
        if not ok:
            return (
                build_error_response(
                    "; ".join(errs),
                    ERR_VALIDATION,
                    {"issues": errs},
                    endpoint=endpoint,
                ),
                None,
                None,
            )

        from web_bridge import normalize_web_form_inputs

        input_data = normalize_web_form_inputs(coerced)
        _t0 = time.perf_counter()
        engine_out = call_analysis_engine(input_data)
        _perf_log.info("[PERF] engine %s took %.3fs", endpoint, time.perf_counter() - _t0)
        if not engine_out.get("success"):
            msg = engine_out.get("message") or "Engine reported failure"
            return (
                build_error_response(
                    msg,
                    ERR_ENGINE,
                    {"engine_message": msg},
                    endpoint=endpoint,
                ),
                None,
                None,
            )
        return None, input_data, engine_out
    except TypeError as e:
        return build_error_response(str(e), ERR_BAD_TYPE, endpoint=endpoint), None, None
    except Exception as e:
        return build_error_response(str(e), ERR_INTERNAL, endpoint=endpoint), None, None


# ---------- P2 Phase3：子接口 data 裁剪 ----------


def _list_str(v: Any) -> list[str]:
    if v is None:
        return []
    if isinstance(v, str):
        s = v.strip()
        return [s] if s else []
    if isinstance(v, list):
        out: list[str] = []
        for x in v:
            if x is None:
                continue
            s = str(x).strip()
            if s:
                out.append(s)
        return out
    return []


def extract_score_breakdown(engine_result: dict) -> dict:
    """从引擎结果抽取评分拆解（复用 top_house_export + explanation_summary）。"""
    engine_result = engine_result if isinstance(engine_result, dict) else {}
    th = engine_result.get("top_house_export")
    if not isinstance(th, dict):
        th = {}
    expl = engine_result.get("explanation_summary")
    if not isinstance(expl, dict):
        expl = {}

    scores = th.get("scores") if isinstance(th.get("scores"), dict) else {}
    reasons = th.get("reasons") if isinstance(th.get("reasons"), dict) else {}
    explain = th.get("explain") if isinstance(th.get("explain"), dict) else {}

    return {
        "score": engine_result.get("property_score"),
        "components": scores or {},
        "score_reasons": reasons or {},
        "weighted_and_factors": {
            "weighted_breakdown": explain.get("weighted_breakdown") or {},
            "top_positive_factors": explain.get("top_positive_factors") or [],
            "top_negative_factors": explain.get("top_negative_factors") or [],
            "recommendation_summary": explain.get("recommendation_summary") or "N/A",
        },
        "explanation_summary": expl or {},
        "house_label": th.get("house_label") or "N/A",
        "rank": th.get("rank"),
    }


def _listing_for_structured_risk(input_data: dict | None) -> dict:
    """把桥接层输入转成 Module3 structured risk 可消费的 listing（缺字段安全）。"""
    if not isinstance(input_data, dict):
        return {}
    bits = []
    if input_data.get("area"):
        bits.append(str(input_data["area"]).strip())
    if input_data.get("postcode"):
        bits.append(str(input_data["postcode"]).strip())
    blob = " ".join(bits).strip()
    return {
        "rent": input_data.get("rent"),
        "notes": blob or "",
        "description": blob or "",
    }


def extract_risk_payload(engine_result: dict, listing_for_m3: dict) -> dict:
    """风险视图：Module3 structured + unified_decision 中风险相关切片。"""
    from contract_risk import calculate_structured_risk_score

    engine_result = engine_result if isinstance(engine_result, dict) else {}
    structured = calculate_structured_risk_score(listing_for_m3)

    p = engine_result.get("unified_decision_payload")
    if not isinstance(p, dict):
        p = {}
    analysis = p.get("analysis") if isinstance(p.get("analysis"), dict) else {}
    uf = p.get("user_facing") if isinstance(p.get("user_facing"), dict) else {}
    trace = p.get("trace") if isinstance(p.get("trace"), dict) else {}
    refs = p.get("references") if isinstance(p.get("references"), dict) else {}
    dec = p.get("decision") if isinstance(p.get("decision"), dict) else {}
    placeholder = (
        engine_result.get("risk_result")
        if isinstance(engine_result.get("risk_result"), dict)
        else {}
    )

    score_val = structured.get("structured_risk_score")
    severity = "N/A"
    if isinstance(score_val, (int, float)):
        if score_val >= 7:
            severity = "high"
        elif score_val >= 4:
            severity = "medium"
        else:
            severity = "low"

    risk_notes = list(structured.get("risk_reasons") or [])
    risk_notes.extend(_list_str(uf.get("risk_note")))

    suggested: list[str] = []
    suggested.extend(_list_str(uf.get("next_step")))
    suggested.extend(_list_str(analysis.get("required_actions_before_proceeding")))
    suggested.extend(_list_str(dec.get("final_action")))

    blockers_trace: list[str] = []
    blockers_trace.extend(_list_str(trace.get("blocker_trace")))
    blockers_trace.extend(_list_str(trace.get("risk_trace_reasons")))

    return {
        "module3_structured": structured,
        "severity_indicator": severity,
        "risk_markers": structured.get("matched_rules") or [],
        "risk_notes": risk_notes,
        "suggested_actions": suggested,
        "decision_risk_signal": dec.get("risk_signal") or "N/A",
        "blockers_and_trace": blockers_trace,
        "references_risk": refs.get("risk_reference")
        if isinstance(refs.get("risk_reference"), dict)
        else {},
        "contract_risk_placeholder": placeholder,
    }


def extract_explain_lists_from_parts(
    analysis: dict,
    user_facing: dict,
    trace: dict,
    explanation_summary: dict,
    decision: dict,
) -> dict[str, list[str]]:
    """从已拆好的块抽取四向列表（供 /explain-only 与批量行复用）。"""
    analysis = analysis if isinstance(analysis, dict) else {}
    uf = user_facing if isinstance(user_facing, dict) else {}
    trace = trace if isinstance(trace, dict) else {}
    expl = explanation_summary if isinstance(explanation_summary, dict) else {}
    dec = decision if isinstance(decision, dict) else {}

    recommended: list[str] = []
    recommended.extend(_list_str(analysis.get("supporting_reasons")))
    recommended.extend(_list_str(uf.get("reason")))
    recommended.extend(_list_str(trace.get("support_trace")))
    recommended.extend(_list_str(expl.get("key_positives")))
    recommended.extend(_list_str(expl.get("top_positive_reasons")))

    concerns: list[str] = []
    concerns.extend(_list_str(analysis.get("primary_blockers")))
    concerns.extend(_list_str(analysis.get("missing_information")))
    concerns.extend(_list_str(trace.get("blocker_trace")))

    risks: list[str] = []
    risks.extend(_list_str(uf.get("risk_note")))
    risks.extend(_list_str(expl.get("key_risks")))
    risks.extend(_list_str(expl.get("top_risk_reasons")))

    next_steps: list[str] = []
    next_steps.extend(_list_str(uf.get("next_step")))
    next_steps.extend(_list_str(analysis.get("recommended_inputs_to_improve_decision")))
    next_steps.extend(_list_str(dec.get("final_action")))

    return {
        "recommended_reasons": recommended,
        "concerns": concerns,
        "risks": risks,
        "next_steps": next_steps,
    }


def extract_explain_payload(engine_result: dict) -> dict:
    """仅用户可读解释：user_facing + 与 Phase4 类似的四向列表（轻量汇总）。"""
    engine_result = engine_result if isinstance(engine_result, dict) else {}
    base = normalize_engine_output(engine_result)
    expl = engine_result.get("explanation_summary")
    if not isinstance(expl, dict):
        expl = {}
    analysis = base.get("analysis") if isinstance(base.get("analysis"), dict) else {}
    uf = base.get("user_facing") if isinstance(base.get("user_facing"), dict) else {}
    trace = base.get("trace") if isinstance(base.get("trace"), dict) else {}
    dec = base.get("decision") if isinstance(base.get("decision"), dict) else {}

    lists = extract_explain_lists_from_parts(analysis, uf, trace, expl, dec)

    return {
        "user_facing": uf,
        "recommended_reasons": lists["recommended_reasons"],
        "concerns": lists["concerns"],
        "risks": lists["risks"],
        "next_steps": lists["next_steps"],
        "explanation_summary": expl,
        "decision": dec,
        "status": base.get("status") if isinstance(base.get("status"), dict) else {},
    }


def modular_analyze_response(raw_body: Any, endpoint: str) -> dict:
    """统一入口：按 endpoint 返回全量或裁剪 data。"""
    try:
        err, inp, eng = run_standard_pipeline(raw_body, endpoint)
        if err:
            return err
        assert eng is not None

        if endpoint == "/analyze":
            return build_success_response(eng, endpoint=endpoint)

        if endpoint == "/score-breakdown":
            data = extract_score_breakdown(eng)
        elif endpoint == "/risk-check":
            data = extract_risk_payload(eng, _listing_for_structured_risk(inp))
        elif endpoint == "/explain-only":
            data = extract_explain_payload(eng)
        else:
            return build_error_response(
                "Unknown endpoint: %s" % endpoint,
                ERR_INTERNAL,
                endpoint=endpoint,
            )

        meta = build_meta(endpoint)
        meta["engine_message"] = eng.get("message") or ""
        return {
            "success": True,
            "data": data,
            "error": None,
            "meta": meta,
        }
    except TypeError as e:
        return build_error_response(str(e), ERR_BAD_TYPE, endpoint=endpoint)
    except Exception as e:
        return build_error_response(str(e), ERR_INTERNAL, endpoint=endpoint)


def analyze_property_request_body(raw_body: Any) -> dict:
    """POST /analyze"""
    return modular_analyze_response(raw_body, "/analyze")


# ---------- P2 Phase4–5：批量分析 + TopN / 对比 / 风险汇总 ----------


def normalize_property_item(item: Any) -> tuple[bool, list[str], dict]:
    """单条房源字段标准化（同单接口）。"""
    if not isinstance(item, dict):
        return False, ["Each property must be a JSON object"], {}
    return normalize_api_input(item)


def analyze_property_item_for_batch(index: int, item: Any) -> dict:
    """对单套房源：normalize_web_form_inputs → run_web_demo_analysis；失败不抛。"""
    if not isinstance(item, dict):
        return {
            "index": index,
            "success": False,
            "error": {"message": "Property must be a JSON object", "type": ERR_VALIDATION},
        }
    try:
        ok, errs, coerced = normalize_property_item(item)
        if not ok:
            return {
                "index": index,
                "success": False,
                "error": {
                    "message": "; ".join(errs),
                    "type": ERR_VALIDATION,
                    "details": {"issues": errs},
                },
            }
        from web_bridge import normalize_web_form_inputs

        input_data = normalize_web_form_inputs(coerced)
        engine_out = call_analysis_engine(input_data)
        if not engine_out.get("success"):
            return {
                "index": index,
                "success": False,
                "error": {
                    "message": engine_out.get("message") or "Engine reported failure",
                    "type": ERR_ENGINE,
                },
            }
        return {
            "index": index,
            "success": True,
            "data": normalize_engine_output(engine_out),
            "input_meta": {
                "rent": input_data.get("rent"),
                "budget": input_data.get("budget"),
                "commute_minutes": input_data.get("commute_minutes"),
                "bedrooms": input_data.get("bedrooms"),
                "bills_included": input_data.get("bills_included"),
            },
        }
    except Exception as e:
        return {
            "index": index,
            "success": False,
            "error": {"message": str(e), "type": ERR_INTERNAL},
        }


def _decision_label(status: dict, decision: dict) -> str:
    if isinstance(status, dict):
        ov = status.get("overall_recommendation")
        if ov is not None and str(ov).strip():
            return str(ov).strip()
    if isinstance(decision, dict):
        fs = decision.get("final_summary")
        if fs is not None and str(fs).strip():
            s = str(fs).strip()
            return s[:240] + ("…" if len(s) > 240 else "")
    return "N/A"


def _decision_code(status: dict, decision: dict) -> str:
    """产品向短码：recommended / not_recommended / uncertain / N/A。"""
    t = (_decision_label(status, decision) or "").lower()
    if not t or t == "n/a":
        return "N/A"
    if any(
        w in t
        for w in (
            "recommend",
            "proceed",
            "strong",
            "good fit",
            "positive",
        )
    ):
        return "recommended"
    if any(w in t for w in ("avoid", "not recommend", "reject", "unsafe", "high risk")):
        return "not_recommended"
    return "uncertain"


def batch_result_row(item_out: dict) -> dict:
    """单项内部结果 → 批量 results[] 行（含 explanation_summary / input_meta 供 Phase5 解释）。"""
    idx = item_out.get("index", -1)
    row: dict[str, Any] = {"index": idx, "success": bool(item_out.get("success"))}
    if not item_out.get("success"):
        row["error"] = item_out.get("error")
        row["score"] = None
        row["decision"] = {}
        row["analysis"] = {}
        row["user_facing"] = {}
        row["references"] = {}
        row["trace"] = {}
        row["status"] = {}
        row["decision_label"] = "N/A"
        row["explanation_summary"] = {}
        row["top_house_export"] = {}
        row["input_meta"] = {}
        return row
    d = item_out["data"]
    st = d.get("status") if isinstance(d.get("status"), dict) else {}
    dec = d.get("decision") if isinstance(d.get("decision"), dict) else {}
    row["error"] = None
    row["score"] = d.get("score")
    row["decision"] = dec
    row["analysis"] = d.get("analysis") if isinstance(d.get("analysis"), dict) else {}
    row["user_facing"] = d.get("user_facing") if isinstance(d.get("user_facing"), dict) else {}
    row["references"] = d.get("references") if isinstance(d.get("references"), dict) else {}
    row["trace"] = d.get("trace") if isinstance(d.get("trace"), dict) else {}
    row["status"] = st
    row["decision_label"] = _decision_label(st, dec)
    row["explanation_summary"] = (
        d.get("explanation_summary") if isinstance(d.get("explanation_summary"), dict) else {}
    )
    th = d.get("top_house_export")
    row["top_house_export"] = th if isinstance(th, dict) else {}
    im = item_out.get("input_meta")
    row["input_meta"] = im if isinstance(im, dict) else {}
    return row


def enrich_batch_result_row(row: dict) -> dict:
    """Phase5：每行增加四向列表 + decision 短码/摘要（不删原 decision 对象）。"""
    if not row.get("success"):
        row["recommended_reasons"] = []
        row["concerns"] = []
        row["risks"] = []
        row["next_steps"] = []
        row["decision_code"] = "N/A"
        row["decision_summary"] = "N/A"
        return row
    lists = extract_explain_lists_from_parts(
        row.get("analysis") or {},
        row.get("user_facing") or {},
        row.get("trace") or {},
        row.get("explanation_summary") or {},
        row.get("decision") or {},
    )
    row["recommended_reasons"] = lists["recommended_reasons"]
    row["concerns"] = lists["concerns"]
    row["risks"] = lists["risks"]
    row["next_steps"] = lists["next_steps"]
    row["decision_code"] = _decision_code(row.get("status") or {}, row.get("decision") or {})
    row["decision_summary"] = row.get("decision_label") or "N/A"
    return row


def _dedupe_preserve(items: list[str], *, cap: int) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for x in items:
        if not isinstance(x, str):
            continue
        k = x.strip().lower()
        if not k or k in seen:
            continue
        seen.add(k)
        out.append(x.strip())
        if len(out) >= cap:
            break
    return out


def extract_batch_recommended_reasons(top_rows: list[dict], *, cap: int = 12) -> list[str]:
    """从 TopN 行汇总推荐要点（去重）。"""
    acc: list[str] = []
    for r in top_rows:
        if not isinstance(r, dict):
            continue
        acc.extend(r.get("recommended_reasons") or [])
    return _dedupe_preserve(acc, cap=cap)


def extract_batch_concern_reasons(rows: list[dict], *, cap: int = 16) -> list[str]:
    """汇总所有成功房源的顾虑。"""
    acc: list[str] = []
    for r in rows:
        if not r.get("success"):
            continue
        acc.extend(r.get("concerns") or [])
    return _dedupe_preserve(acc, cap=cap)


def build_comparison_summary(
    rows: list[dict],
    ranking: list[dict],
    top_rec: dict,
) -> str:
    """一句话/短多行对比；失败返回 N/A 文案，不抛异常。"""
    try:
        ok = [r for r in rows if r.get("success")]
        if not ok:
            return "N/A — No successful analyses in this batch."
        top1 = top_rec.get("top1")
        t1_idx = top1.get("index") if isinstance(top1, dict) else None
        t1_score = top1.get("score") if isinstance(top1, dict) else None
        lines: list[str] = []
        if t1_idx is not None and t1_score is not None:
            try:
                lines.append(
                    "Highest property score: index %s at %.2f."
                    % (t1_idx, float(t1_score))
                )
            except (TypeError, ValueError):
                lines.append(
                    "Top-ranked listing: index %s (score N/A)." % t1_idx
                )
        elif t1_idx is not None:
            lines.append("Top-ranked listing: index %s." % t1_idx)

        # 预算敏感：租金最低的成功项
        def _rent(r: dict) -> float | None:
            im = r.get("input_meta") if isinstance(r.get("input_meta"), dict) else {}
            v = im.get("rent")
            if v is None:
                return None
            try:
                return float(v)
            except (TypeError, ValueError):
                return None

        scored_rents = [(r, _rent(r)) for r in ok]
        valid = [(r, x) for r, x in scored_rents if x is not None]
        if valid:
            rmin, rv = min(valid, key=lambda t: t[1])
            lines.append(
                "Most budget-friendly rent: index %s at £%s/month (among successful runs)."
                % (rmin.get("index"), rv)
            )

        # 通勤最短
        def _commute(r: dict) -> float | None:
            im = r.get("input_meta") if isinstance(r.get("input_meta"), dict) else {}
            v = im.get("commute_minutes")
            if v is None:
                return None
            try:
                return float(v)
            except (TypeError, ValueError):
                return None

        comms = [(r, _commute(r)) for r in ok]
        cvalid = [(r, x) for r, x in comms if x is not None]
        if cvalid:
            rbest, cv = min(cvalid, key=lambda t: t[1])
            lines.append(
                "Shortest commute: index %s at %s minutes."
                % (rbest.get("index"), int(cv) if cv == int(cv) else cv)
            )

        if not lines:
            return "N/A — Insufficient fields to build comparison lines."
        return "\n".join(lines)
    except Exception:
        return "N/A — Comparison summary unavailable."


def build_risk_summary(rows: list[dict]) -> dict:
    """跨房源风险要点汇总（仅基于已有解释字段）。"""
    try:
        acc: list[str] = []
        for r in rows:
            if not r.get("success"):
                continue
            acc.extend(r.get("risks") or [])
            rs = r.get("decision") or {}
            if isinstance(rs, dict) and rs.get("risk_signal"):
                acc.append(str(rs.get("risk_signal")))
        uniq = _dedupe_preserve(acc, cap=24)
        if not uniq:
            return {
                "summary_text": "No aggregated risk notes across listings (N/A).",
                "distinct_count": 0,
                "samples": [],
            }
        head = uniq[:5]
        return {
            "summary_text": " | ".join(head),
            "distinct_count": len(uniq),
            "samples": uniq[:10],
        }
    except Exception:
        return {
            "summary_text": "N/A — Risk summary unavailable.",
            "distinct_count": 0,
            "samples": [],
        }


def rank_batch_results(rows: list[dict]) -> list[dict]:
    """默认按 score 降序；无分/非数值的成功项次之；失败项最后。"""

    def sort_key(r: dict) -> tuple:
        if not r.get("success"):
            return (3, 0.0, r.get("index", 0))
        s = r.get("score")
        if s is None:
            return (2, 0.0, r.get("index", 0))
        try:
            return (1, -float(s), r.get("index", 0))
        except (TypeError, ValueError):
            return (2, 0.0, r.get("index", 0))

    ordered = sorted(rows, key=sort_key)
    ranking: list[dict] = []
    for pos, row in enumerate(ordered):
        ranking.append(
            {
                "rank": pos + 1,
                "index": row["index"],
                "score": row.get("score"),
                "decision": row.get("decision_label") or "N/A",
                "success": row.get("success"),
            }
        )
    return ranking


def build_top_recommendations(rows: list[dict], ranking: list[dict]) -> dict:
    """Top1 与 Top3（成功项，按 ranking 顺序）；Phase5 标准命名。"""
    by_idx = {r["index"]: r for r in rows}
    ok_rank = [x for x in ranking if x.get("success")]
    top3_indices = [x["index"] for x in ok_rank[:3]]
    top1_row = by_idx.get(top3_indices[0]) if top3_indices else None
    top3_rows = [by_idx[i] for i in top3_indices if i in by_idx]
    return {
        "top1": top1_row,
        "top3": top3_rows,
        "sorted_indices_by_score": [x["index"] for x in ok_rank],
    }


def analyze_batch_request_body(raw_body: Any) -> dict:
    """
    POST /analyze-batch。
    整包格式错误 → success false；单项失败 → 该行 success false，整包仍 success true。
    """
    try:
        if not isinstance(raw_body, dict):
            return build_error_response(
                "Request body must be a JSON object",
                ERR_VALIDATION,
                endpoint=BATCH_ENDPOINT,
                api_version=BATCH_API_VERSION,
            )
        props = raw_body.get("properties")
        if props is None:
            return build_error_response(
                "Missing required field 'properties'",
                ERR_VALIDATION,
                endpoint=BATCH_ENDPOINT,
                api_version=BATCH_API_VERSION,
            )
        if not isinstance(props, list):
            return build_error_response(
                "Field 'properties' must be an array",
                ERR_VALIDATION,
                endpoint=BATCH_ENDPOINT,
                api_version=BATCH_API_VERSION,
            )
        if len(props) > _BATCH_MAX_ITEMS:
            return build_error_response(
                "Too many properties: %d (max %d)" % (len(props), _BATCH_MAX_ITEMS),
                ERR_VALIDATION,
                endpoint=BATCH_ENDPOINT,
                api_version=BATCH_API_VERSION,
            )

        def _process_one(idx_item: tuple[int, Any]) -> dict:
            i, item = idx_item
            out = analyze_property_item_for_batch(i, item)
            row = batch_result_row(out)
            enrich_batch_result_row(row)
            return row

        _bt0 = time.perf_counter()
        workers = min(_BATCH_WORKERS, max(len(props), 1))
        if workers <= 1 or len(props) <= 1:
            rows = [_process_one((i, item)) for i, item in enumerate(props)]
        else:
            rows_by_idx: dict[int, dict] = {}
            with ThreadPoolExecutor(max_workers=workers) as pool:
                futures = {
                    pool.submit(_process_one, (i, item)): i
                    for i, item in enumerate(props)
                }
                for fut in as_completed(futures):
                    idx = futures[fut]
                    rows_by_idx[idx] = fut.result()
            rows = [rows_by_idx[i] for i in range(len(props))]
        _perf_log.info(
            "[PERF] batch engine: %d items in %.3fs (%.3fs/item, workers=%d)",
            len(props),
            time.perf_counter() - _bt0,
            (time.perf_counter() - _bt0) / max(len(props), 1),
            workers,
        )
        ranking = rank_batch_results(rows)
        top_rec = build_top_recommendations(rows, ranking)
        top3 = top_rec.get("top3") or []
        rec_reasons = extract_batch_recommended_reasons(top3)
        concern_reasons = extract_batch_concern_reasons(rows)
        comparison_summary = build_comparison_summary(rows, ranking, top_rec)
        risk_summary = build_risk_summary(rows)
        meta = build_meta(BATCH_ENDPOINT, api_version=BATCH_API_VERSION)
        succ = sum(1 for r in rows if r.get("success"))
        meta["batch_summary"] = {
            "requested": len(props),
            "succeeded": succ,
            "failed": len(props) - succ,
        }
        return {
            "success": True,
            "data": {
                "count": len(props),
                "results": rows,
                "ranking": ranking,
                "top_recommendation": top_rec,
                "top_1_recommendation": top_rec.get("top1"),
                "top_3_recommendations": top3,
                "comparison_summary": comparison_summary,
                "recommendation_reasons": rec_reasons,
                "concern_reasons": concern_reasons,
                "risk_summary": risk_summary,
            },
            "error": None,
            "meta": meta,
        }
    except Exception as e:
        return build_error_response(
            str(e),
            ERR_INTERNAL,
            endpoint=BATCH_ENDPOINT,
            api_version=BATCH_API_VERSION,
        )


def legacy_ui_result_from_standard_envelope(envelope: dict) -> dict:
    """
    标准封套 → app_web 内部 result。
    子接口（无全量 decision 块）时 payload 可能为空，页面区块可为空。
    """
    envelope = envelope if isinstance(envelope, dict) else {}
    if "data" not in envelope and "unified_decision_payload" in envelope:
        return envelope

    ep = "/analyze"
    m = envelope.get("meta")
    if isinstance(m, dict) and m.get("endpoint"):
        ep = str(m.get("endpoint"))

    out: dict[str, Any] = {
        "success": bool(envelope.get("success")),
        "message": "",
        "property_score": None,
        "unified_decision_payload": {},
        "unified_decision": {},
        "final_recommendation": {},
        "explanation_summary": {},
        "explanation": {},
        "risk_result": {},
        "top_house_export": {},
        "explain_result": {},
        "_api_meta": build_meta(ep),
    }

    if not envelope.get("success"):
        err = envelope.get("error")
        if isinstance(err, dict):
            out["message"] = err.get("message") or "Unknown error"
        else:
            out["message"] = str(err or "Unknown error")
        out["risk_result"] = {"status": "error", "message": out["message"]}
        out["success"] = False
        return out

    data = envelope.get("data")
    if not isinstance(data, dict):
        out["success"] = False
        out["message"] = "Invalid API response: missing or invalid data"
        out["risk_result"] = {"status": "error", "message": out["message"]}
        return out

    meta = envelope.get("meta") if isinstance(envelope.get("meta"), dict) else build_meta(ep)
    out["_api_meta"] = meta

    # 全量 /analyze（必须用 meta.endpoint 区分，避免与 explain-only 的 decision 字段冲突）
    if ep == "/analyze":
        out["property_score"] = data.get("score")
        out["message"] = meta.get("engine_message") or ""
        out["unified_decision_payload"] = {
            "status": data.get("status") if isinstance(data.get("status"), dict) else {},
            "decision": data.get("decision") if isinstance(data.get("decision"), dict) else {},
            "analysis": data.get("analysis") if isinstance(data.get("analysis"), dict) else {},
            "user_facing": data.get("user_facing")
            if isinstance(data.get("user_facing"), dict)
            else {},
            "references": data.get("references")
            if isinstance(data.get("references"), dict)
            else {},
            "trace": data.get("trace") if isinstance(data.get("trace"), dict) else {},
        }
        out["final_recommendation"] = (
            data.get("final_recommendation")
            if isinstance(data.get("final_recommendation"), dict)
            else {}
        )
        out["explanation_summary"] = (
            data.get("explanation_summary")
            if isinstance(data.get("explanation_summary"), dict)
            else {}
        )
        out["explanation"] = (
            data.get("explanation") if isinstance(data.get("explanation"), dict) else {}
        )
        out["unified_decision"] = (
            data.get("unified_decision")
            if isinstance(data.get("unified_decision"), dict)
            else {}
        )
        out["risk_result"] = (
            data.get("risk_result") if isinstance(data.get("risk_result"), dict) else {}
        )
        th = data.get("top_house_export")
        out["top_house_export"] = th if isinstance(th, dict) else {}
        ex = data.get("explain_result")
        out["explain_result"] = ex if isinstance(ex, dict) else {}
        return out

    # 子接口：尽量填充可映射字段，其余留空
    out["property_score"] = data.get("score")
    out["message"] = meta.get("engine_message") or ""
    if ep == "/explain-only":
        uf = dict(data.get("user_facing") or {}) if isinstance(data.get("user_facing"), dict) else {}
        if data.get("risks"):
            uf["risk_note"] = data.get("risks")
        if data.get("next_steps"):
            uf["next_step"] = data.get("next_steps")
        out["unified_decision_payload"] = {
            "status": data.get("status") if isinstance(data.get("status"), dict) else {},
            "decision": data.get("decision") if isinstance(data.get("decision"), dict) else {},
            "analysis": {
                "supporting_reasons": data.get("recommended_reasons") or [],
                "primary_blockers": data.get("concerns") or [],
            },
            "user_facing": uf,
            "references": {},
            "trace": {},
        }
        out["explanation_summary"] = (
            data.get("explanation_summary")
            if isinstance(data.get("explanation_summary"), dict)
            else {}
        )
    elif ep == "/score-breakdown":
        out["unified_decision_payload"] = {}
        out["explanation_summary"] = (
            data.get("explanation_summary")
            if isinstance(data.get("explanation_summary"), dict)
            else {}
        )
    elif ep == "/risk-check":
        out["risk_result"] = {
            "status": "structured",
            "module3": data.get("module3_structured"),
            "severity": data.get("severity_indicator"),
            "markers": data.get("risk_markers"),
            "placeholder": data.get("contract_risk_placeholder"),
        }
        out["unified_decision_payload"] = {
            "status": {},
            "decision": {"risk_signal": data.get("decision_risk_signal")},
            "analysis": {
                "primary_blockers": data.get("blockers_and_trace") or [],
            },
            "user_facing": {
                "risk_note": data.get("risk_notes") or [],
                "next_step": data.get("suggested_actions") or [],
            },
            "references": {
                "risk_reference": data.get("references_risk") or {},
            },
            "trace": {},
        }
    else:
        out["unified_decision_payload"] = {}

    return out


def envelope_from_engine_result(engine_result: dict) -> dict:
    """本地引擎 → 与 HTTP /analyze 相同封套。"""
    engine_result = engine_result if isinstance(engine_result, dict) else {}
    if not engine_result.get("success"):
        msg = engine_result.get("message") or "Analysis did not complete successfully"
        return build_error_response(msg, ERR_ENGINE, endpoint="/analyze")
    return build_success_response(engine_result, endpoint="/analyze")
