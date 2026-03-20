# P1 Phase1–3: RentalAI Web UI
# Phase3: 结果卡片结构化展示 + 页面字段分区
#
# 启动（在 rental_app 目录下）:
#   streamlit run app_web.py
# 浏览器: http://localhost:8501
#
# 依赖: pip install -r requirements.txt  (含 streamlit)

import streamlit as st

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


# ---------- 页面配置 ----------

st.set_page_config(page_title="RentalAI", page_icon="🏠", layout="wide")

st.title("RentalAI Decision Dashboard")
st.caption("P1 Phase3: 结构化结果展示 · 输入 → 分析 → 分区卡片")

# --- 输入表单（Phase2 逻辑保留）---
st.subheader("Property input")
st.caption("数字留空将使用默认：rent 1200 / budget 1500 / commute 30 / bedrooms 2")

c1, c2, c3 = st.columns(3)
with c1:
    rent_in = st.text_input("Rent (£/month)", value="1200", help="月租，可留空用默认")
    budget_in = st.text_input("Budget (£/month)", value="1500", help="预算")
    commute_in = st.text_input("Commute (minutes)", value="30", help="通勤分钟")
with c2:
    bedrooms_in = st.text_input("Bedrooms", value="2", help="卧室数")
    distance_in = st.text_input("Distance (optional)", value="", help="到目标点距离（与引擎一致，可空）")
    bills_included = st.checkbox("Bills included", value=False)
with c3:
    area_in = st.text_input("Area", value="", placeholder="e.g. E1")
    postcode_in = st.text_input("Postcode", value="", placeholder="e.g. E1 6AN")
    target_postcode_in = st.text_input("Target postcode (optional)", value="")

st.markdown("---")

analyze = st.button("Analyze Property", type="primary")

if not analyze:
    st.info("填写表单后点击 **Analyze Property** 开始分析。")
else:
    raw_form = {
        "rent": rent_in,
        "budget": budget_in,
        "commute_minutes": commute_in,
        "bedrooms": bedrooms_in,
        "distance": distance_in,
        "bills_included": bills_included,
        "area": area_in,
        "postcode": postcode_in,
        "target_postcode": target_postcode_in,
    }

    result = None
    err_msg = None
    try:
        from web_bridge import normalize_web_form_inputs, run_web_demo_analysis

        input_data = normalize_web_form_inputs(raw_form)
        with st.spinner("Running analysis..."):
            result = run_web_demo_analysis(input_data)
    except Exception as e:
        err_msg = str(e)
        result = {"success": False, "message": err_msg}

    if not result:
        st.error("No result returned.")
        st.stop()

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

    # ========== Overview / Summary ==========
    st.markdown("## Overview / Summary")
    with st.container():
        col_o1, col_o2 = st.columns([1, 2])
        with col_o1:
            st.markdown("**Analysis status**")
            if err_msg:
                st.error("Failed")
            elif ok:
                st.success("Success")
            else:
                st.warning("Not successful")
            st.markdown("**success**")
            st.write(str(ok))
        with col_o2:
            msg = result.get("message") or ""
            st.markdown("**Message**")
            st.write(_display_text(msg, "N/A") if msg or err_msg else "N/A")
            one_line = safe_get(user_facing, "summary") if isinstance(user_facing, dict) else "N/A"
            if one_line == "N/A":
                one_line = _display_text(decision.get("final_summary") if decision else None, "N/A")
            st.markdown("**Quick read**")
            st.write(one_line)

    st.divider()

    # ========== Score ==========
    st.markdown("## Score")
    with st.container():
        score = result.get("property_score")
        if score is not None:
            try:
                st.metric(label="Property score (final_score)", value="%.2f" % float(score))
            except (TypeError, ValueError):
                st.metric(label="Property score", value=_display_text(score, "N/A"))
        else:
            st.info("No score — N/A")

    st.divider()

    # ========== Decision ==========
    st.markdown("## Decision")
    with st.container():
        st.markdown("**Overall recommendation**")
        rec_val = safe_get(status, "overall_recommendation") if status else "N/A"
        st.write(rec_val)
        st.markdown("**Confidence**")
        st.write(_display_text(safe_get(status, "decision_confidence"), "N/A"))
        st.markdown("**Confidence reason**")
        st.write(_display_text(safe_get(status, "confidence_reason"), "N/A"))
        st.markdown("---")
        format_decision_block(decision)

    st.divider()

    # ========== Analysis ==========
    st.markdown("## Analysis")
    with st.container():
        format_analysis_block(analysis)

    st.divider()

    # ========== User facing explanation ==========
    st.markdown("## User-facing explanation")
    with st.container():
        format_user_facing_block(user_facing)

    st.divider()

    # ========== References ==========
    st.markdown("## References")
    with st.container():
        format_references_block(references)

    st.divider()

    # ========== Risk（占位，主流程可见）==========
    st.markdown("## Risk analysis")
    with st.container():
        risk = result.get("risk_result") or {}
        st.info(_display_text(risk.get("message"), "No contract risk input"))

    # ========== Trace / Debug（弱化，默认折叠）==========
    with st.expander("Trace & debug info", expanded=False):
        st.caption("Technical trace — collapsed by default")
        format_trace_block(trace, compact=True)
        st.markdown("**Explanation summary (engine)**")
        expl = result.get("explanation_summary") or {}
        if expl:
            st.write(_display_text(expl.get("summary"), "N/A"))
            pos = expl.get("key_positives") or expl.get("top_positive_reasons") or []
            neg = expl.get("key_risks") or expl.get("top_risk_reasons") or []
            if pos:
                st.markdown("**Positives**")
                for p in pos[:5]:
                    st.markdown(f"- {_display_text(p)}")
            if neg:
                st.markdown("**Risks**")
                for n in neg[:5]:
                    st.markdown(f"- {_display_text(n)}")
        else:
            st.caption("No data")
        st.markdown("**Final house recommendation (raw)**")
        frec = result.get("final_recommendation") or {}
        if frec:
            st.json(frec)
        else:
            st.caption("Empty")
        st.markdown("**Full bridge result (debug)**")
        st.json({k: v for k, v in result.items() if k != "explanation"})

st.markdown("---")
st.caption("RentalAI | Module2 + Module7 | P1 Phase3 Web UI")
