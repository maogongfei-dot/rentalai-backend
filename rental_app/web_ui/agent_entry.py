# P5 Phase1–3: Agent 入口 — 规则解析 + 表单同步 + analyze-batch 调度
from __future__ import annotations

from typing import Any

from web_ui.agent_runner import agent_intent_sparse_warning, run_agent_intent_analysis
from web_ui.intent_to_payload import build_analyze_raw_form_from_intent
from web_ui.rental_intent import AgentRentalRequest
from web_ui.rental_intent_parser import intent_has_key_signals, parse_rental_intent
from web_ui.result_ui import section_header

# Session keys（与 app_web 约定，避免与表单 key 冲突）
P5_KEY_PHASE = "p5_agent_phase"
P5_KEY_NL = "p5_agent_nl_input"
P5_KEY_INTENT = "p5_agent_last_intent"
P5_KEY_HINT = "p5_agent_form_hint"

# Phase1–2 流程 + Phase3 提交与结果
PHASE_IDLE = "idle"
PHASE_PARSING_PREVIEW = "parsing_preview"
PHASE_PARSED_RESULT = "parsed_result"
PHASE_READY_FOR_ANALYSIS = "ready_for_analysis"  # 保留名：可与「仅填表」扩展共用
PHASE_SUBMITTING = "submitting"
PHASE_ANALYSIS_SUCCESS = "analysis_success"
PHASE_ANALYSIS_ERROR = "analysis_error"


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


def _process_agent_batch_submit(
    st: Any,
    *,
    lab: dict[str, str],
    use_local: bool,
    api_base_url: str,
) -> None:
    """Continue → submitting 后在本轮渲染早期执行 batch。"""
    if st.session_state.get(P5_KEY_PHASE) != PHASE_SUBMITTING:
        return
    it = AgentRentalRequest.from_dict(st.session_state.get(P5_KEY_INTENT) or {})
    with st.spinner(lab.get("p5_agent_spinner_submit", "Running agent batch…")):
        resp, err, payload = run_agent_intent_analysis(
            it,
            use_local=use_local,
            api_base_url=api_base_url,
        )
    if err and not resp:
        st.session_state[P5_KEY_PHASE] = PHASE_ANALYSIS_ERROR
        st.session_state["p5_agent_last_error"] = err
        st.session_state["p2_batch_last"] = {
            "success": False,
            "error": {"message": err},
        }
        return
    if resp is not None:
        st.session_state["p2_batch_last"] = resp
        st.session_state["p2_batch_last_request"] = payload
        if resp.get("success"):
            st.session_state[P5_KEY_PHASE] = PHASE_ANALYSIS_SUCCESS
            st.session_state["p5_agent_last_error"] = ""
        else:
            st.session_state[P5_KEY_PHASE] = PHASE_ANALYSIS_ERROR
            em = ""
            er = resp.get("error")
            if isinstance(er, dict):
                em = str(er.get("message") or "")
            st.session_state["p5_agent_last_error"] = em or "Batch returned success=false"
    else:
        st.session_state[P5_KEY_PHASE] = PHASE_ANALYSIS_ERROR
        st.session_state["p5_agent_last_error"] = err or "Unknown error"


def apply_agent_intent_to_form_keys(
    intent: AgentRentalRequest,
    form_keys: dict[str, str],
    st_session: Any,
) -> list[str]:
    """
    将 intent 转为与 **analyze-batch 单条 property** 一致的数值，并写入表单 session。
    """
    hints: list[str] = []
    raw = build_analyze_raw_form_from_intent(intent)
    s = st_session
    s[form_keys["rent"]] = raw["rent"]
    s[form_keys["budget"]] = raw["budget"]
    s[form_keys["commute_minutes"]] = raw["commute_minutes"]
    s[form_keys["bedrooms"]] = raw["bedrooms"]
    s[form_keys["distance"]] = raw["distance"]
    s[form_keys["bills_included"]] = raw["bills_included"]
    s[form_keys["area"]] = raw["area"]
    s[form_keys["postcode"]] = raw["postcode"]
    s[form_keys["target_postcode"]] = raw["target_postcode"]

    w = agent_intent_sparse_warning(intent)
    if w:
        hints.append(w)
    if intent.source_preference:
        hints.append(
            "**Source preference** is copied into the **area** text only (API has no source field)."
        )
    return hints


def render_p5_agent_entry(
    st: Any,
    *,
    lab: dict[str, str],
    form_keys: dict[str, str],
    use_local: bool,
    api_base_url: str,
) -> None:
    """
    自然语言 → Parse → Continue：**同步表单并调用 analyze-batch**（单条场景），结果写入 `p2_batch_last`。
    """
    init_p5_agent_session(st)
    if st.session_state.pop("p5_refinement_parse_reminder", False):
        st.info(lab.get("p5_agent_refine_parse_reminder", "Scroll to **AI Agent** and click **Parse request**."))
    if st.session_state.pop("p5_refinement_snippet_added", False):
        st.success(
            lab.get(
                "p5_refinement_snippet_ok",
                "Added a line to your request box — click **Parse request** when ready.",
            )
        )
    _consume_parsing_preview(st)
    _process_agent_batch_submit(
        st,
        lab=lab,
        use_local=use_local,
        api_base_url=api_base_url,
    )

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
            st.session_state["p5_agent_last_error"] = ""

        st.button(lab["p5_agent_clear_button"], on_click=_go_clear, type="secondary")

    with b3:
        st.caption(lab["p5_agent_single_turn_note"])

    intent_dict = st.session_state.get(P5_KEY_INTENT)
    _show_preview = phase in (
        PHASE_PARSED_RESULT,
        PHASE_ANALYSIS_SUCCESS,
        PHASE_ANALYSIS_ERROR,
    )
    if _show_preview and isinstance(intent_dict, dict):
        st.markdown("**%s**" % lab["p5_agent_raw_heading"])
        st.code((intent_dict.get("raw_query") or "").strip() or "(empty)", language=None)

        st.markdown("**%s**" % lab["p5_agent_structured_heading"])
        st.json(intent_dict)

        _it = AgentRentalRequest.from_dict(intent_dict)
        _rich = intent_has_key_signals(_it)

        if phase == PHASE_ANALYSIS_SUCCESS:
            st.success(lab["p5_agent_batch_success"])
        elif phase == PHASE_ANALYSIS_ERROR:
            _em = st.session_state.get("p5_agent_last_error") or lab["unknown_error"]
            st.error(lab["p5_agent_batch_error"] % _em)
        elif _rich:
            st.success(lab["p5_agent_preview_rich"])
        else:
            st.info(lab["p5_agent_preview_note"])

        st.markdown("**%s**" % lab["p5_agent_readiness_heading"])
        if phase == PHASE_ANALYSIS_SUCCESS:
            st.write(lab["p5_agent_after_batch_success"])
        elif phase == PHASE_ANALYSIS_ERROR:
            st.write(lab["p5_agent_after_batch_error"])
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
                st.session_state[P5_KEY_PHASE] = PHASE_SUBMITTING

            st.button(
                lab["p5_agent_continue_button"],
                on_click=_continue,
                type="primary",
                help=lab["p5_agent_continue_help"],
            )
        with cta2:
            st.caption(lab["p5_agent_continue_caption"])

    hint = st.session_state.get(P5_KEY_HINT) or ""
    if hint and phase in (PHASE_ANALYSIS_SUCCESS, PHASE_ANALYSIS_ERROR):
        st.warning(hint)

    st.divider()
