# P2 Phase1: API 层辅助 — 输入规范化、调用 web_bridge、组装对外 JSON
# 与 Streamlit 解耦：同一套 build 结果可供 HTTP 与本地复用

from __future__ import annotations

from typing import Any

# 与 web 表单一致的字段名，便于 UI 直接 POST


def normalize_api_input(raw: Any) -> tuple[bool, list[str], dict]:
    """
    将 JSON 体转为可交给 normalize_web_form_inputs 的 dict。
    - 缺字段：不写入，交给 web_bridge 默认值
    - 显式提供但无法解析的类型：返回错误文案
    """
    errors: list[str] = []
    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        return False, ["Request body must be a JSON object"], {}

    out: dict[str, Any] = dict(raw)

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
        if sk in out and out[sk] is not None:
            out[sk] = str(out[sk]).strip() or None

    if "bills_included" in out:
        b = out["bills_included"]
        if isinstance(b, bool):
            pass
        elif isinstance(b, (int, float)):
            out["bills_included"] = bool(int(b))
        elif isinstance(b, str):
            out["bills_included"] = b.strip().lower() in (
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
    """统一走 web_bridge，不重复实现分析逻辑。"""
    from web_bridge import run_web_demo_analysis

    return run_web_demo_analysis(input_data)


def build_api_response(engine_result: dict) -> dict:
    """
    对外稳定 JSON：含 success、score 别名、payload 子块、error、以及 UI 所需的透传字段。
    """
    engine_result = engine_result if isinstance(engine_result, dict) else {}
    p = engine_result.get("unified_decision_payload")
    if not isinstance(p, dict):
        p = {}

    success = bool(engine_result.get("success"))
    msg = engine_result.get("message") or ""
    err = None
    if not success and msg:
        err = msg
    elif not success:
        err = "Analysis did not complete successfully"

    return {
        "success": success,
        "property_score": engine_result.get("property_score"),
        "score": engine_result.get("property_score"),
        "message": msg,
        "decision": p.get("decision") if isinstance(p.get("decision"), dict) else {},
        "analysis": p.get("analysis") if isinstance(p.get("analysis"), dict) else {},
        "user_facing": p.get("user_facing") if isinstance(p.get("user_facing"), dict) else {},
        "references": p.get("references") if isinstance(p.get("references"), dict) else {},
        "trace": p.get("trace") if isinstance(p.get("trace"), dict) else {},
        "error": err,
        # 与 app_web 现有展示兼容（与直接调 run_web_demo_analysis 一致）
        "unified_decision_payload": p,
        "unified_decision": engine_result.get("unified_decision") or {},
        "final_recommendation": engine_result.get("final_recommendation") or {},
        "explanation_summary": engine_result.get("explanation_summary") or {},
        "explanation": engine_result.get("explanation") or {},
        "risk_result": engine_result.get("risk_result")
        if isinstance(engine_result.get("risk_result"), dict)
        else {"status": "placeholder", "message": "No contract risk input"},
    }


def analyze_property_request_body(raw_body: Any) -> dict:
    """
    供 FastAPI 路由调用：校验 JSON → normalize_web_form_inputs → 引擎 → build_api_response。
    任意异常吞掉并返回 success=False，不抛到 ASGI。
    """
    try:
        ok, errs, coerced = normalize_api_input(raw_body)
        if not ok:
            return {
                "success": False,
                "property_score": None,
                "score": None,
                "message": "; ".join(errs),
                "decision": {},
                "analysis": {},
                "user_facing": {},
                "references": {},
                "trace": {},
                "error": "; ".join(errs),
                "unified_decision_payload": {},
                "unified_decision": {},
                "final_recommendation": {},
                "explanation_summary": {},
                "explanation": {},
                "risk_result": {"status": "error", "message": "Invalid input"},
            }

        from web_bridge import normalize_web_form_inputs

        input_data = normalize_web_form_inputs(coerced)
        engine_out = call_analysis_engine(input_data)
        return build_api_response(engine_out)
    except Exception as e:
        em = str(e)
        return {
            "success": False,
            "property_score": None,
            "score": None,
            "message": em,
            "decision": {},
            "analysis": {},
            "user_facing": {},
            "references": {},
            "trace": {},
            "error": em,
            "unified_decision_payload": {},
            "unified_decision": {},
            "final_recommendation": {},
            "explanation_summary": {},
            "explanation": {},
            "risk_result": {"status": "error", "message": em},
        }
