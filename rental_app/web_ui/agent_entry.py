# P5 Phase1–2: Agent 入口 UI（Streamlit）— 规则解析预览 + 表单回填
from __future__ import annotations

from typing import Any

from web_ui.rental_intent import AgentRentalRequest
from web_ui.rental_intent_parser import intent_has_key_signals, parse_rental_intent
from web_ui.result_ui import section_header

# Session keys（与 app_web 约定，避免与表单 key 冲突）
P5_KEY_PHASE = "p5_agent_phase"
P5_KEY_NL = "p5_agent_nl_input"
P5_KEY_INTENT = "p5_agent_last_intent"
P5_KEY_HINT = "p5_agent_form_hint"

# 与产品文档一致的阶段名（便于 Phase2/3 扩展）
PHASE_IDLE = "idle"
PHASE_PARSING_PREVIEW = "parsing_preview"
PHASE_PARSED_RESULT = "parsed_result"
PHASE_READY_FOR_ANALYSIS = "ready_for_analysis"


def init_p5_agent_session(st: Any) -> None:
    if P5_KEY_PHASE not in st.session_state:
        st.session_state[P5_KEY_PHASE] = PHASE_IDLE


def _consume_parsing_preview(st: Any) -> None:
    """由 parsing_preview 自动进入 parsed_result（P5 Phase2 规则解析，无 LLM）。"""
    if st.session_state.get(P5_KEY_PHASE) != PHASE_PARSING_PREVIEW:
        return
    raw = st.session_state.get(P5_KEY_NL, "")
    if not isinstance(raw, str):
        raw = str(raw) if raw is not None else ""
    intent = parse_rental_intent(raw)
    st.session_state[P5_KEY_INTENT] = intent.to_dict()
    st.session_state[P5_KEY_PHASE] = PHASE_PARSED_RESULT


def apply_agent_intent_to_form_keys(
    intent: AgentRentalRequest,
    form_keys: dict[str, str],
    st_session: Any,
) -> list[str]:
    """
    将结构化预览同步到现有 analyze 表单 session 键；返回未写入表单的提示（如无 commute）。
    """
    hints: list[str] = []
    s = st_session

    if intent.max_rent is not None:
        rv = intent.max_rent
        s[form_keys["rent"]] = str(int(rv)) if rv == int(rv) else str(rv)
        # 预算未识别时与租金对齐，减少必填阻塞（用户可再改）
        if not (s.get(form_keys.get("budget") or "") or "").strip():
            s[form_keys["budget"]] = s[form_keys["rent"]]

    if intent.bedrooms is not None:
        s[form_keys["bedrooms"]] = str(intent.bedrooms)

    if intent.max_commute_minutes is not None:
        s[form_keys["commute_minutes"]] = str(intent.max_commute_minutes)

    if intent.preferred_area:
        s[form_keys["area"]] = intent.preferred_area

    if intent.target_postcode:
        s[form_keys["target_postcode"]] = intent.target_postcode

    if intent.bills_included is not None:
        s[form_keys["bills_included"]] = bool(intent.bills_included)

    extra: list[str] = []
    if intent.property_type:
        extra.append("Property type: %s" % intent.property_type)
    if intent.furnished is not None:
        extra.append("Furnished: %s" % ("yes" if intent.furnished else "no"))
    if intent.source_preference:
        extra.append("Source: %s" % intent.source_preference)
    if intent.notes:
        extra.append(intent.notes)

    if not (s.get(form_keys["commute_minutes"]) or "").strip():
        hints.append("Commute (minutes) is still required for **Analyze Property**.")

    if not (s.get(form_keys["budget"]) or "").strip():
        hints.append("Budget is still required — please fill or use **Load Demo Data**.")

    if extra:
        hints.append("Not mapped to form (saved as hint): " + "; ".join(extra))

    return hints


def render_p5_agent_entry(
    st: Any,
    *,
    lab: dict[str, str],
    form_keys: dict[str, str],
) -> None:
    """
    主入口：自然语言框 + Parse + 预览 JSON + Continue to Analysis。
    调用方需在首屏对 session 调用 init_p5_agent_session；本函数开头会消费 parsing_preview。
    """
    init_p5_agent_session(st)
    _consume_parsing_preview(st)

    phase = st.session_state.get(P5_KEY_PHASE, PHASE_IDLE)

    section_header(
        st,
        lab["p5_agent_section_title"],
        level=3,
        caption=lab["p5_agent_section_caption"],
    )

    st.caption("%s **%s**" % (lab["p5_agent_phase_label"], phase.replace("_", " ")))

    st.text_area(
        lab["p5_agent_input_label"],
        height=110,
        key=P5_KEY_NL,
        placeholder=lab["p5_agent_input_placeholder"],
        help=lab["p5_agent_input_help"],
    )

    b1, b2, b3 = st.columns([1, 1, 2])
    with b1:

        def _go_parse() -> None:
            st.session_state[P5_KEY_PHASE] = PHASE_PARSING_PREVIEW

        st.button(
            lab["p5_agent_parse_button"],
            type="primary",
            on_click=_go_parse,
            help=lab["p5_agent_parse_help"],
        )
    with b2:

        def _go_clear() -> None:
            st.session_state[P5_KEY_PHASE] = PHASE_IDLE
            st.session_state[P5_KEY_INTENT] = None
            st.session_state[P5_KEY_HINT] = ""
            st.session_state[P5_KEY_NL] = ""

        st.button(lab["p5_agent_clear_button"], on_click=_go_clear, type="secondary")

    with b3:
        st.caption(lab["p5_agent_single_turn_note"])

    # 预览区：parsed_result 或 ready 时仍展示最后 intent
    intent_dict = st.session_state.get(P5_KEY_INTENT)
    if phase in (PHASE_PARSED_RESULT, PHASE_READY_FOR_ANALYSIS) and isinstance(intent_dict, dict):
        st.markdown("**%s**" % lab["p5_agent_raw_heading"])
        st.code((intent_dict.get("raw_query") or "").strip() or "(empty)", language=None)

        st.markdown("**%s**" % lab["p5_agent_structured_heading"])
        st.json(intent_dict)

        ready = phase == PHASE_READY_FOR_ANALYSIS
        _it = AgentRentalRequest.from_dict(intent_dict)
        _rich = intent_has_key_signals(_it)

        if ready:
            st.success(lab["p5_agent_ready_banner"])
        elif _rich:
            st.success(lab["p5_agent_preview_rich"])
        else:
            st.info(lab["p5_agent_preview_note"])

        st.markdown("**%s**" % lab["p5_agent_readiness_heading"])
        if ready:
            st.write(lab["p5_agent_ready_yes"])
        elif _rich:
            st.write(lab["p5_agent_ready_partial"])
        else:
            st.write(lab["p5_agent_ready_sparse"])

        cta1, cta2 = st.columns(2)
        with cta1:

            def _continue() -> None:
                it = AgentRentalRequest.from_dict(
                    st.session_state.get(P5_KEY_INTENT) or {}
                )
                h = apply_agent_intent_to_form_keys(it, form_keys, st.session_state)
                st.session_state[P5_KEY_HINT] = "\n".join(h) if h else ""
                st.session_state[P5_KEY_PHASE] = PHASE_READY_FOR_ANALYSIS

            st.button(
                lab["p5_agent_continue_button"],
                on_click=_continue,
                type="primary",
                help=lab["p5_agent_continue_help"],
            )
        with cta2:
            st.caption(lab["p5_agent_continue_caption"])

    hint = st.session_state.get(P5_KEY_HINT) or ""
    if hint and phase == PHASE_READY_FOR_ANALYSIS:
        st.warning(hint)

    st.divider()
