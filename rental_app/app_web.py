# P1 Phase1–6 + P2 Phase1–4: Web UI（HTTP 封套 + 可选 /analyze-batch 烟测）
# Phase4: 结果解释增强 — 推荐 / 顾虑 / 风险 / 下一步 分开展示
# Phase5: 输入校验、示例预填、错误提示、Reset form
# Phase6: 页面收口、统一文案、演示顺序、弱化调试区
#
# 启动（在 rental_app 目录下）:
#   streamlit run app_web.py
# 浏览器: http://localhost:8501
#
# 依赖: pip install -r requirements.txt  (含 streamlit)

import os

import streamlit as st

# ---------- P1 Phase5: 输入校验 / 示例数据 / 错误提示 ----------

# Session keys for form widgets（与 st.text_input(..., key=) 一致）
_FORM_KEYS = {
    "rent": "form_rent",
    "budget": "form_budget",
    "commute_minutes": "form_commute_minutes",
    "bedrooms": "form_bedrooms",
    "distance": "form_distance",
    "bills_included": "form_bills_included",
    "area": "form_area",
    "postcode": "form_postcode",
    "target_postcode": "form_target_postcode",
}

# 推荐示例（与需求一致）；首次进入页面会预填
_DEMO_FORM_STATE = {
    _FORM_KEYS["rent"]: "1200",
    _FORM_KEYS["budget"]: "1500",
    _FORM_KEYS["commute_minutes"]: "25",
    _FORM_KEYS["bedrooms"]: "2",
    _FORM_KEYS["distance"]: "",
    _FORM_KEYS["bills_included"]: True,
    _FORM_KEYS["area"]: "",
    _FORM_KEYS["postcode"]: "",
    _FORM_KEYS["target_postcode"]: "",
}

# Clear form：空字符串 + bills 关（用户需自行填写或再点 Load example）
_CLEAR_FORM_STATE = {
    _FORM_KEYS["rent"]: "",
    _FORM_KEYS["budget"]: "",
    _FORM_KEYS["commute_minutes"]: "",
    _FORM_KEYS["bedrooms"]: "",
    _FORM_KEYS["distance"]: "",
    _FORM_KEYS["bills_included"]: False,
    _FORM_KEYS["area"]: "",
    _FORM_KEYS["postcode"]: "",
    _FORM_KEYS["target_postcode"]: "",
}


def init_form_session_state() -> None:
    """首次访问时预填示例数据（不覆盖用户已改过的 session）。"""
    for k, v in _DEMO_FORM_STATE.items():
        if k not in st.session_state:
            st.session_state[k] = v


def load_demo_values() -> dict:
    """返回示例表单状态副本（供 Load example 批量写回）。"""
    return dict(_DEMO_FORM_STATE)


def _parse_non_negative_float(raw: str, field_label: str) -> tuple[float | None, str | None]:
    """解析非负浮点；错误返回 (None, error_message)。"""
    s = (raw or "").strip()
    if not s:
        return None, f"{field_label} is required"
    try:
        v = float(s)
    except (TypeError, ValueError):
        return None, f"{field_label} must be a numeric value"
    if v < 0:
        return None, f"{field_label} must be a non-negative number"
    return v, None


def _parse_non_negative_int(raw: str, field_label: str) -> tuple[int | None, str | None]:
    """解析非负整数（允许 2.0 这类输入）。"""
    s = (raw or "").strip()
    if not s:
        return None, f"{field_label} is required"
    try:
        v = float(s)
    except (TypeError, ValueError):
        return None, f"{field_label} must be a numeric value"
    if v < 0:
        return None, f"{field_label} must be a non-negative number"
    return int(v), None


def validate_inputs(raw: dict) -> tuple[bool, list[str]]:
    """
    Phase5 基础校验：rent/budget/commute/bedrooms 必填、数字、>=0；
    bills_included 可布尔化；area/postcode/target_postcode/distance 可空，不报错。
    """
    errors: list[str] = []
    rent = raw.get("rent")
    budget = raw.get("budget")
    commute = raw.get("commute_minutes")
    bedrooms = raw.get("bedrooms")
    bills = raw.get("bills_included")

    _, e = _parse_non_negative_float(str(rent) if rent is not None else "", "Rent (£/month)")
    if e:
        errors.append(e)

    _, e = _parse_non_negative_float(str(budget) if budget is not None else "", "Budget (£/month)")
    if e:
        errors.append(e)

    _, e = _parse_non_negative_int(str(commute) if commute is not None else "", "Commute minutes")
    if e:
        errors.append(e)

    _, e = _parse_non_negative_int(str(bedrooms) if bedrooms is not None else "", "Bedrooms")
    if e:
        errors.append(e)

    # Checkbox 一般为 bool；若来自其它来源则尝试转换
    if bills is None:
        errors.append("Bills included must be yes/no or a checkbox value")
    elif isinstance(bills, str):
        sl = bills.strip().lower()
        if sl not in ("", "yes", "y", "true", "1", "no", "n", "false", "0", "包", "包含"):
            if sl:  # 非空且无法识别
                errors.append("Bills included must be a clear yes/no value")

    return (len(errors) == 0, errors)


def build_error_message(errors: list[str]) -> str:
    """合并为一段可读错误文案（单行换行展示）。"""
    if not errors:
        return ""
    return "\n".join(f"• {e}" for e in errors)


def collect_raw_form_from_session() -> dict:
    """从 session_state 组装与原先 raw_form 相同结构的 dict。"""
    return {
        "rent": st.session_state.get(_FORM_KEYS["rent"], ""),
        "budget": st.session_state.get(_FORM_KEYS["budget"], ""),
        "commute_minutes": st.session_state.get(_FORM_KEYS["commute_minutes"], ""),
        "bedrooms": st.session_state.get(_FORM_KEYS["bedrooms"], ""),
        "distance": st.session_state.get(_FORM_KEYS["distance"], ""),
        "bills_included": st.session_state.get(_FORM_KEYS["bills_included"], False),
        "area": st.session_state.get(_FORM_KEYS["area"], ""),
        "postcode": st.session_state.get(_FORM_KEYS["postcode"], ""),
        "target_postcode": st.session_state.get(_FORM_KEYS["target_postcode"], ""),
    }


def normalize_form_values(raw: dict) -> dict:
    """校验通过后交给 web_bridge 做类型与空字段规范化（与引擎入参对齐）。"""
    from web_bridge import normalize_web_form_inputs

    return normalize_web_form_inputs(raw)


def run_analysis_for_ui(
    raw_form: dict,
    *,
    use_local: bool,
    api_base_url: str,
    api_endpoint: str = "/analyze",
) -> tuple[dict | None, str | None]:
    """
    P2 Phase3：HTTP 可调 /analyze、/score-breakdown、/risk-check、/explain-only；
    本地模式等价全量 /analyze。
    """
    from api_analysis import envelope_from_engine_result, legacy_ui_result_from_standard_envelope

    if use_local:
        try:
            from web_bridge import run_web_demo_analysis

            input_data = normalize_form_values(raw_form)
            engine = run_web_demo_analysis(input_data)
            envelope = envelope_from_engine_result(engine)
            return legacy_ui_result_from_standard_envelope(envelope), None
        except Exception as e:
            return None, str(e)

    import requests

    path = api_endpoint if str(api_endpoint).startswith("/") else "/%s" % api_endpoint
    url = "%s%s" % ((api_base_url or "").rstrip("/"), path)
    try:
        resp = requests.post(url, json=raw_form, timeout=120)
        resp.raise_for_status()
        data = resp.json()
        if not isinstance(data, dict):
            return None, "API returned non-JSON object"
        return legacy_ui_result_from_standard_envelope(data), None
    except requests.RequestException as e:
        return None, "API request failed: %s" % (e,)
    except ValueError as e:
        return None, "Invalid JSON from API: %s" % (e,)


# ---------- P1 Phase6: Demo 收口 / 统一展示文案 ----------


def normalize_display_labels() -> dict:
    """区块与指标英文标签（单一来源，避免 Overview / Decision / Score 前后不一致）。"""
    return {
        "input_section": "Property details",
        "actions_section": "Actions",
        "validation_section": "Validation",
        "errors_section": "Errors",
        "overview": "Overview",
        "score": "Property score",
        "decision": "Decision",
        "decision_caption": "High-level recommendation and confidence from the scoring engine.",
        "recommended": "Recommended reasons",
        "concerns": "Concerns",
        "risks": "Risks",
        "next_steps": "Next steps",
        "analysis_detail": "Analysis (structured detail)",
        "user_facing": "Narrative summary",
        "references": "References",
        "contract_risk": "Contract risk",
        "debug_expander": "Technical trace & debug",
    }


def build_page_header(*, show_demo_hint: bool = True) -> None:
    """主标题 + 一句话产品说明；可选 Demo 引导（不抢主视觉）。"""
    st.title("RentalAI · Rental decision demo")
    st.markdown(
        "Compare a listing to your **budget** and **commute**, then review **overview**, "
        "**property score**, **decision**, and **recommended reasons**, **concerns**, **risks**, and **next steps**."
    )
    if show_demo_hint:
        st.caption(
            "Demo: sample values are pre-filled — click **Analyze Property** for a one-click run."
        )


def render_demo_footer() -> None:
    """页脚 prototype 声明（Phase6 验收用）。"""
    st.markdown("---")
    st.caption(
        "_This is a prototype demo for rental property analysis. "
        "Results are illustrative and not legal, financial, or investment advice._"
    )
    st.caption("RentalAI P1 · Module2 + Module7 · Web UI")


# ---------- P1 Phase3: 安全展示辅助函数 ----------


def safe_get(obj, *keys, default="N/A"):
    """嵌套 dict 安全取值；缺省或空返回 default。"""
    cur = obj
    for k in keys:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(k)
    if cur is None:
        return default
    if isinstance(cur, str) and not cur.strip():
        return default
    if isinstance(cur, (list, dict)) and len(cur) == 0:
        return default
    return cur


def _display_text(val, empty="No data"):
    """标量转展示字符串。"""
    if val is None:
        return empty
    if isinstance(val, str) and not val.strip():
        return empty
    return str(val)


def format_decision_block(decision: dict) -> None:
    """payload.decision 结构化展示（非 raw 一行）。"""
    if not isinstance(decision, dict) or not decision:
        st.caption("No data")
        return
    for key in (
        "final_summary",
        "decision_focus",
        "final_action",
        "house_signal",
        "risk_signal",
    ):
        label = key.replace("_", " ").title()
        val = decision.get(key)
        st.markdown(f"**{label}**")
        st.write(_display_text(val, "N/A"))


def format_analysis_block(analysis: dict) -> None:
    """payload.analysis：列表用 bullet，dict 嵌套简短展示。"""
    if not isinstance(analysis, dict) or not analysis:
        st.caption("Empty")
        return
    for key, val in analysis.items():
        label = str(key).replace("_", " ").title()
        st.markdown(f"**{label}**")
        if isinstance(val, list):
            if not val:
                st.caption("Empty")
            else:
                for item in val:
                    if isinstance(item, (dict, list)):
                        st.json(item)
                    else:
                        st.markdown(f"- {_display_text(item, 'N/A')}")
        elif isinstance(val, dict):
            if not val:
                st.caption("Empty")
            else:
                st.json(val)
        else:
            st.write(_display_text(val, "N/A"))


def format_user_facing_block(uf: dict) -> None:
    """用户可读解释区。"""
    if not isinstance(uf, dict) or not uf:
        st.caption("No data")
        return
    summary = uf.get("summary")
    st.markdown("**Summary**")
    st.info(_display_text(summary, "N/A"))

    list_keys = ("reason", "risk_note", "next_step", "explanation")
    for lk in list_keys:
        items = uf.get(lk) or []
        title = lk.replace("_", " ").title()
        st.markdown(f"**{title}**")
        if not isinstance(items, list):
            st.write(_display_text(items, "N/A"))
        elif not items:
            st.caption("Empty")
        else:
            for x in items:
                st.markdown(f"- {_display_text(x, 'N/A')}")


def format_references_block(refs: dict) -> None:
    """references 分区展示。"""
    if not isinstance(refs, dict) or not refs:
        st.caption("No data")
        return
    for name in ("house_reference", "risk_reference"):
        sub = refs.get(name)
        st.markdown(f"**{name.replace('_', ' ').title()}**")
        if not isinstance(sub, dict) or not sub:
            st.caption("Empty")
        else:
            for k, v in sub.items():
                st.markdown(f"- **{k}:** {_display_text(v, 'N/A')}")


def format_trace_block(trace: dict, *, compact: bool = True) -> None:
    """Trace 调试向展示。"""
    if not isinstance(trace, dict) or not trace:
        st.caption("Empty")
        return
    ts = trace.get("trace_summary")
    st.markdown("**Trace summary**")
    st.write(_display_text(ts, "N/A"))
    list_fields = (
        ("decision_trace", "Decision trace"),
        ("blocker_trace", "Blocker trace"),
        ("support_trace", "Support trace"),
        ("house_trace_reasons", "House trace"),
        ("risk_trace_reasons", "Risk trace"),
    )
    for field, title in list_fields:
        lst = trace.get(field) or []
        st.markdown(f"**{title}**")
        if not isinstance(lst, list) or not lst:
            st.caption("Empty")
        else:
            show = lst[:4] if compact else lst
            for line in show:
                st.markdown(f"- {_display_text(line, 'N/A')}")


# ---------- P1 Phase4: 解释层提取与格式化 ----------


def _list_str(v):
    """任意值 → 非空字符串列表。"""
    if v is None:
        return []
    if isinstance(v, str):
        s = v.strip()
        return [s] if s else []
    if isinstance(v, list):
        out = []
        for x in v:
            if x is None:
                continue
            s = str(x).strip()
            if s:
                out.append(s)
        return out
    return []


def _dedupe_preserve(items: list) -> list:
    """去重保序，忽略大小写键。"""
    seen = set()
    out = []
    for x in items:
        if not isinstance(x, str):
            continue
        k = x.strip().lower()
        if not k or k in ("n/a", "none", "empty"):
            continue
        if k not in seen:
            seen.add(k)
            out.append(x.strip())
    return out


def extract_recommended_reasons(
    decision: dict,
    analysis: dict,
    user_facing: dict,
    trace: dict,
    result: dict,
) -> list:
    """合并 user_facing / analysis / trace / explanation_snapshot 中的正向理由。"""
    out = []
    if isinstance(analysis, dict):
        out.extend(_list_str(analysis.get("supporting_reasons")))
    if isinstance(user_facing, dict):
        out.extend(_list_str(user_facing.get("reason")))
    if isinstance(trace, dict):
        out.extend(_list_str(trace.get("support_trace")))
        out.extend(_list_str(trace.get("house_trace_reasons")))
    expl = (result or {}).get("explanation_summary") or {}
    if isinstance(expl, dict):
        out.extend(_list_str(expl.get("key_positives")))
        out.extend(_list_str(expl.get("top_positive_reasons")))
        out.extend(_list_str(expl.get("why_recommend")))
    # final_recommendation 主理由一句
    frec = (result or {}).get("final_recommendation") or {}
    if isinstance(frec, dict):
        pr = frec.get("primary_recommendation") or {}
        if isinstance(pr, dict) and pr.get("reason"):
            out.extend(_list_str(pr.get("reason")))
    return _dedupe_preserve(out)


def extract_concerns(decision: dict, analysis: dict, user_facing: dict, trace: dict) -> list:
    """顾虑 / 为何不直接推进：blockers、缺失信息、局限、风险侧 trace。"""
    out = []
    if isinstance(analysis, dict):
        out.extend(_list_str(analysis.get("primary_blockers")))
        out.extend(_list_str(analysis.get("missing_information")))
        out.extend(_list_str(analysis.get("assessment_limitations")))
    if isinstance(trace, dict):
        out.extend(_list_str(trace.get("blocker_trace")))
        out.extend(_list_str(trace.get("risk_trace_reasons")))
    expl = (user_facing or {}).get("explanation") if isinstance(user_facing, dict) else []
    # explanation 链里常含 “However …” — 整段作为一条补充顾虑（避免拆句复杂逻辑）
    for line in _list_str(expl):
        if any(w in line.lower() for w in ("however", "unsafe", "not yet", "clarify", "missing", "gap", "unresolved")):
            out.append(line)
    return _dedupe_preserve(out)


def extract_risks(analysis: dict, user_facing: dict, trace: dict, references: dict) -> list:
    """风险提示：用户 risk_note + 参考摘要中的警示。"""
    out = []
    if isinstance(user_facing, dict):
        out.extend(_list_str(user_facing.get("risk_note")))
    if isinstance(trace, dict):
        out.extend(_list_str(trace.get("blocker_trace")))
    if isinstance(references, dict):
        for key in ("house_reference", "risk_reference"):
            sub = references.get(key) or {}
            if isinstance(sub, dict):
                summ = sub.get("summary") or sub.get("risk_level")
                out.extend(_list_str(summ) if isinstance(summ, str) else _list_str(summ))
    return _dedupe_preserve(out)


def extract_next_steps(decision: dict, user_facing: dict, analysis: dict) -> list:
    """下一步用户指引：final_action + next_step + 必做动作 + 建议补充信息。"""
    out = []
    if isinstance(decision, dict):
        out.extend(_list_str(decision.get("final_action")))
        out.extend(_list_str(decision.get("decision_focus")))
    if isinstance(user_facing, dict):
        out.extend(_list_str(user_facing.get("next_step")))
        out.extend(_list_str(user_facing.get("explanation")))
    if isinstance(analysis, dict):
        out.extend(_list_str(analysis.get("required_actions_before_proceeding")))
        out.extend(_list_str(analysis.get("recommended_inputs_to_improve_decision")))
    return _dedupe_preserve(out)


def format_reason_list(title: str, reasons: list, *, empty_label: str = "No clear reason provided") -> None:
    """统一 bullet 展示理由列表。"""
    if title and str(title).strip():
        st.markdown(f"**{title}**")
    if not reasons:
        st.caption(empty_label)
        return
    for r in reasons:
        st.markdown(f"- {_display_text(r, 'N/A')}")


def render_explanation_highlights(
    decision: dict,
    analysis: dict,
    user_facing: dict,
    trace: dict,
    references: dict,
    result: dict,
) -> None:
    """Phase4/6 解释区：纵向顺序 — Recommended → Concerns → Risks → Next steps（与验收顺序一致）。"""
    lab = normalize_display_labels()
    rec = extract_recommended_reasons(decision, analysis, user_facing, trace, result)
    con = extract_concerns(decision, analysis, user_facing, trace)
    risks = extract_risks(analysis, user_facing, trace, references)
    steps = extract_next_steps(decision, user_facing, analysis)

    st.markdown(f"## {lab['recommended']}")
    st.caption("Why the engine leans positive (when data supports it).")
    format_reason_list("", rec)
    if rec:
        st.success("These factors support moving forward (subject to your own checks).")
    elif not (con or risks or steps):
        st.caption("No structured positive reasons extracted for this run.")

    st.divider()
    st.markdown(f"## {lab['concerns']}")
    st.caption("Gaps, blockers, or reasons to pause before committing.")
    format_reason_list("", con)
    if con:
        st.warning("Review these before you proceed.")

    st.divider()
    st.markdown(f"## {lab['risks']}")
    st.caption("Uncertainty and downside signals.")
    format_reason_list("", risks)
    if risks:
        st.error("Treat these as signals to verify or mitigate.")

    st.divider()
    st.markdown(f"## {lab['next_steps']}")
    st.caption("Concrete follow-ups from the decision and user-facing guidance.")
    format_reason_list("", steps)
    if steps:
        st.info("Work through these in order where relevant.")

    if not rec and not con and not risks and not steps:
        st.caption("No structured explanation blocks were extracted from this run.")


# ---------- 页面配置 ----------

st.set_page_config(page_title="RentalAI Demo", page_icon="🏠", layout="wide")

init_form_session_state()

lab = normalize_display_labels()
build_page_header(show_demo_hint=True)

# --- P2：侧栏 API / 本地 + 可选子接口路径 ---
st.sidebar.markdown("### Backend (P2)")
_use_local = st.sidebar.checkbox(
    "Use local engine (bypass API)",
    value=os.environ.get("RENTALAI_USE_LOCAL", "").strip().lower() in ("1", "true", "yes"),
    help="On = in-process full analysis (same as /analyze). Modular paths require API.",
)
_api_default = os.environ.get("RENTALAI_API_URL", "http://127.0.0.1:8000").strip()
_api_base = st.sidebar.text_input(
    "API base URL",
    value=_api_default or "http://127.0.0.1:8000",
    disabled=_use_local,
    help="Example: http://127.0.0.1:8000 — start with: uvicorn api_server:app --port 8000",
)
_api_endpoint = st.sidebar.selectbox(
    "API endpoint",
    options=["/analyze", "/score-breakdown", "/risk-check", "/explain-only"],
    index=0,
    disabled=_use_local,
    help="P2 Phase3 modular APIs; default /analyze keeps full dashboard data.",
)
if _use_local:
    st.sidebar.caption("Local mode always uses full engine output (≈ POST /analyze).")
st.sidebar.caption("Start API: `uvicorn api_server:app --host 127.0.0.1 --port 8000`")

# --- Phase6: 输入区（表单 → 再操作按钮，顺序与验收一致）---
st.subheader(lab["input_section"])
st.caption(
    "Required: rent, budget, commute, and bedrooms (non-negative numbers). "
    "Optional: area, postcode, target postcode, distance (invalid distance is ignored server-side)."
)

c1, c2, c3 = st.columns(3)
with c1:
    st.text_input("Rent (£/month)", key=_FORM_KEYS["rent"], help="Required, non-negative number")
    st.text_input("Budget (£/month)", key=_FORM_KEYS["budget"], help="Required, non-negative number")
    st.text_input("Commute (minutes)", key=_FORM_KEYS["commute_minutes"], help="Required, non-negative integer")
with c2:
    st.text_input("Bedrooms", key=_FORM_KEYS["bedrooms"], help="Required, non-negative integer")
    st.text_input(
        "Distance (optional)",
        key=_FORM_KEYS["distance"],
        help="Optional; non-numeric values are ignored and do not block submit",
    )
    st.checkbox("Bills included", key=_FORM_KEYS["bills_included"])
with c3:
    st.text_input("Area", key=_FORM_KEYS["area"], placeholder="e.g. E1")
    st.text_input("Postcode", key=_FORM_KEYS["postcode"], placeholder="e.g. E1 6AN")
    st.text_input("Target postcode (optional)", key=_FORM_KEYS["target_postcode"])

st.markdown("---")
st.subheader(lab["actions_section"])
ba, bb, bc = st.columns([1, 1, 2])
with ba:
    if st.button("Load Demo Data", type="secondary", help="Restore recommended sample values"):
        for k, v in load_demo_values().items():
            st.session_state[k] = v
        st.rerun()
with bb:
    if st.button("Reset Form", type="secondary", help="Clear fields; use Load Demo Data or enter values again"):
        for k, v in _CLEAR_FORM_STATE.items():
            st.session_state[k] = v
        st.rerun()
with bc:
    analyze = st.button("Analyze Property", type="primary", use_container_width=True)

if not analyze:
    st.info(
        "Use **Load Demo Data** to restore samples, **Reset Form** to clear, then **Analyze Property** to run. "
        "Invalid inputs show under **Validation** without crashing the app."
    )
else:
    raw_form = collect_raw_form_from_session()

    valid, validation_errors = validate_inputs(raw_form)
    if not valid:
        st.markdown(f"### {lab['validation_section']}")
        st.error("Please fix the following before re-running analysis.")
        st.warning(build_error_message(validation_errors))
        st.stop()

    result = None
    err_msg = None
    try:
        with st.spinner("Running analysis..."):
            result, transport_err = run_analysis_for_ui(
                raw_form,
                use_local=_use_local,
                api_base_url=_api_base,
                api_endpoint=_api_endpoint,
            )
        if transport_err:
            err_msg = transport_err
            result = result or {
                "success": False,
                "message": transport_err,
                "unified_decision_payload": {},
            }
    except Exception as e:
        err_msg = str(e)
        result = {"success": False, "message": err_msg, "unified_decision_payload": {}}

    if err_msg:
        st.markdown(f"### {lab['errors_section']}")
        st.error("Unexpected error while running analysis (shown below).")
        st.warning(_display_text(err_msg, "Unknown error"))

    if not result:
        st.error("No result returned.")
        st.stop()

    # P2 Phase2：API 业务失败时优先展示 error.message（已映射到 result["message"]）
    if not err_msg and not result.get("success") and result.get("message"):
        st.error(result["message"])

    payload = result.get("unified_decision_payload") or {}
    status = payload.get("status") if isinstance(payload.get("status"), dict) else {}
    decision = payload.get("decision") if isinstance(payload.get("decision"), dict) else {}
    analysis = payload.get("analysis") if isinstance(payload.get("analysis"), dict) else {}
    user_facing = payload.get("user_facing") if isinstance(payload.get("user_facing"), dict) else {}
    references = payload.get("references") if isinstance(payload.get("references"), dict) else {}
    trace = payload.get("trace") if isinstance(payload.get("trace"), dict) else {}

    # 无 payload 时从 raw unified_decision 兜底
    if not payload and isinstance(result.get("unified_decision"), dict):
        ud = result["unified_decision"]
        status = {
            "overall_recommendation": ud.get("overall_recommendation"),
            "decision_confidence": ud.get("decision_confidence"),
            "confidence_reason": ud.get("confidence_reason"),
        }
        decision = {
            "final_summary": ud.get("final_summary"),
            "decision_focus": ud.get("decision_focus"),
            "final_action": ud.get("final_action"),
            "house_signal": ud.get("house_signal"),
            "risk_signal": ud.get("risk_signal"),
        }
        analysis = {
            "supporting_reasons": ud.get("supporting_reasons") or [],
            "primary_blockers": ud.get("primary_blockers") or [],
            "missing_information": ud.get("missing_information") or [],
        }
        user_facing = {
            "summary": ud.get("user_facing_summary"),
            "reason": ud.get("user_facing_reason") or [],
            "risk_note": ud.get("user_facing_risk_note") or [],
            "next_step": ud.get("user_facing_next_step") or [],
            "explanation": ud.get("user_facing_explanation") or [],
        }
        references = {
            "house_reference": ud.get("house_reference") or {},
            "risk_reference": ud.get("risk_reference") or {},
        }
        trace = {
            "trace_summary": ud.get("trace_summary"),
            "decision_trace": ud.get("decision_trace") or [],
            "blocker_trace": ud.get("blocker_trace") or [],
        }

    ok = bool(result.get("success"))

    # ========== Phase6 结果顺序：Overview → Property score → Decision → 四块解释 → 补充区 → References → 占位风险 → Debug ==========
    st.markdown(f"## {lab['overview']}")
    with st.container():
        col_o1, col_o2 = st.columns([1, 2])
        with col_o1:
            st.markdown("**Run status**")
            if err_msg:
                st.error("Failed")
            elif ok:
                st.success("Completed")
            else:
                st.warning("Completed with issues")
            st.caption(f"Engine success flag: `{ok}`")
        with col_o2:
            msg = result.get("message") or ""
            st.markdown("**Engine message**")
            st.write(_display_text(msg, "N/A") if msg or err_msg else "N/A")
            one_line = safe_get(user_facing, "summary") if isinstance(user_facing, dict) else "N/A"
            if one_line == "N/A":
                one_line = _display_text(decision.get("final_summary") if decision else None, "N/A")
            st.markdown("**At a glance**")
            st.write(one_line)

    st.divider()

    st.markdown(f"## {lab['score']}")
    st.caption("Standard field `data.score` (mapped from engine final / property score).")
    with st.container():
        score = result.get("property_score")
        if score is not None:
            try:
                st.metric(label=lab["score"], value="%.2f" % float(score))
            except (TypeError, ValueError):
                st.metric(label=lab["score"], value=_display_text(score, "N/A"))
        else:
            st.info("No property score returned for this run (N/A).")

    st.divider()

    st.markdown(f"## {lab['decision']}")
    st.caption(lab["decision_caption"])
    with st.container():
        st.markdown("**Overall recommendation**")
        rec_val = safe_get(status, "overall_recommendation") if status else "N/A"
        st.write(rec_val)
        st.markdown("**Decision confidence**")
        st.write(_display_text(safe_get(status, "decision_confidence"), "N/A"))
        st.markdown("**Why this confidence level**")
        st.write(_display_text(safe_get(status, "confidence_reason"), "N/A"))
        st.markdown("---")
        st.markdown("**Decision detail**")
        format_decision_block(decision)

    st.divider()

    render_explanation_highlights(
        decision, analysis, user_facing, trace, references, result
    )

    st.divider()

    st.markdown(f"## {lab['analysis_detail']}")
    with st.container():
        format_analysis_block(analysis)

    st.divider()

    st.markdown(f"## {lab['user_facing']}")
    with st.container():
        format_user_facing_block(user_facing)

    st.divider()

    st.markdown(f"## {lab['references']}")
    with st.container():
        format_references_block(references)

    st.divider()

    st.markdown(f"## {lab['contract_risk']}")
    st.caption("Contract / clause risk module — placeholder in P1 Web UI.")
    with st.container():
        risk = result.get("risk_result") or {}
        st.info(_display_text(risk.get("message"), "No contract risk input for this demo."))

    # 调试区：默认折叠 + 弱 caption，避免抢主流程视觉
    with st.expander(lab["debug_expander"], expanded=False):
        st.caption("For developers only — not required for the demo walkthrough.")
        format_trace_block(trace, compact=True)
        st.markdown("**Engine explanation snapshot**")
        expl = result.get("explanation_summary") or {}
        if expl:
            st.write(_display_text(expl.get("summary"), "N/A"))
            pos = expl.get("key_positives") or expl.get("top_positive_reasons") or []
            neg = expl.get("key_risks") or expl.get("top_risk_reasons") or []
            if pos:
                st.markdown("**Positives (engine)**")
                for p in pos[:5]:
                    st.markdown(f"- {_display_text(p)}")
            if neg:
                st.markdown("**Risks (engine)**")
                for n in neg[:5]:
                    st.markdown(f"- {_display_text(n)}")
        else:
            st.caption("No data")
        st.markdown("**Final recommendation (raw JSON)**")
        frec = result.get("final_recommendation") or {}
        if frec:
            st.json(frec)
        else:
            st.caption("Empty")
        st.markdown("**Bridge payload (debug)**")
        st.json({k: v for k, v in result.items() if k != "explanation"})

# --- P2 Phase4–5：批量接口 + 轻量结果展示区 ---
_DEFAULT_BATCH_JSON = """{
  "properties": [
    {"rent": 1200, "budget": 1500, "commute_minutes": 25, "bedrooms": 2, "bills_included": true},
    {"rent": 950, "budget": 1500, "commute_minutes": 40, "bedrooms": 1, "bills_included": false},
    {"rent": 1400, "budget": 1500, "commute_minutes": 15, "bedrooms": 2, "bills_included": true}
  ]
}"""
with st.expander("P2 Phase5 — Batch API (`POST /analyze-batch`)", expanded=False):
    st.caption("Uses **API base URL** above. Disabled when **Use local engine** is on (batch is HTTP-only here).")
    _batch_ta = st.text_area("Request JSON", value=_DEFAULT_BATCH_JSON, height=220, key="p2_batch_json")
    if st.button("Run batch request", key="p2_batch_run"):
        if _use_local:
            st.warning("Turn off **Use local engine** and ensure the API is running to test `/analyze-batch`.")
        else:
            import json

            import requests

            try:
                _payload = json.loads(_batch_ta)
            except json.JSONDecodeError as ex:
                st.error("Invalid JSON: %s" % ex)
            else:
                try:
                    _bu = _api_base.rstrip("/")
                    _br = requests.post("%s/analyze-batch" % _bu, json=_payload, timeout=180)
                    _br.raise_for_status()
                    _bj = _br.json()
                    st.session_state["p2_batch_last"] = _bj
                    with st.expander("Raw JSON response", expanded=False):
                        st.json(_bj)
                except Exception as ex:
                    st.error(_display_text(str(ex), "Request failed"))

    _last_batch = st.session_state.get("p2_batch_last")
    if isinstance(_last_batch, dict) and _last_batch.get("success"):
        _bd = _last_batch.get("data")
        if isinstance(_bd, dict):
            st.divider()
            st.markdown("##### Batch results (Phase5)")
            st.markdown("**Comparison summary**")
            st.text(_bd.get("comparison_summary") or "N/A")
            _rs = _bd.get("risk_summary")
            if isinstance(_rs, dict):
                st.markdown("**Risk summary**")
                st.caption(_rs.get("summary_text") or "N/A")
            st.markdown("**Ranking**")
            st.dataframe(_bd.get("ranking") or [], use_container_width=True, hide_index=True)
            _t1 = _bd.get("top_1_recommendation")
            if isinstance(_t1, dict) and _t1.get("success"):
                st.markdown(
                    "**Top 1** — index `%s` · score `%s` · `%s`"
                    % (
                        _t1.get("index"),
                        _t1.get("score"),
                        _t1.get("decision_code") or _t1.get("decision_summary") or "N/A",
                    )
                )
                st.caption("Recommended reasons (sample)")
                for _ln in (_t1.get("recommended_reasons") or [])[:6]:
                    st.markdown("- %s" % _display_text(_ln, ""))
                st.caption("Concerns (sample)")
                for _ln in (_t1.get("concerns") or [])[:4]:
                    st.markdown("- %s" % _display_text(_ln, ""))
            _t3 = _bd.get("top_3_recommendations") or []
            if _t3:
                st.markdown("**Top 3 indices**")
                st.write(
                    [
                        {
                            "index": x.get("index"),
                            "score": x.get("score"),
                            "code": x.get("decision_code"),
                        }
                        for x in _t3
                        if isinstance(x, dict)
                    ]
                )
            for _r in _bd.get("results") or []:
                if not isinstance(_r, dict) or not _r.get("success"):
                    continue
                with st.expander("Listing index %s — score %s" % (_r.get("index"), _r.get("score")), expanded=False):
                    st.markdown("**decision_code:** `%s`" % (_r.get("decision_code") or "N/A"))
                    st.markdown("**Recommended**")
                    for _ln in (_r.get("recommended_reasons") or [])[:8]:
                        st.markdown("- %s" % _display_text(_ln, ""))
                    st.markdown("**Concerns**")
                    for _ln in (_r.get("concerns") or [])[:6]:
                        st.markdown("- %s" % _display_text(_ln, ""))

render_demo_footer()
