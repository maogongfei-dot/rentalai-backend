# P5 Phase1–5: Agent 入口 — 统一状态名 + 解析 + batch 调度
from __future__ import annotations

from typing import Any

from web_ui.agent_flow import (
    P5_KEY_PHASE,
    PHASE_ANALYSIS_ERROR,
    PHASE_ANALYSIS_SUCCESS,
    PHASE_IDLE,
    PHASE_PARSED,
    PHASE_PARSING,
    PHASE_SUBMITTING,
    agent_refinement_available,
    format_agent_phase_caption,
    migrate_agent_phase,
)
from web_ui.agent_runner import agent_intent_sparse_warning, run_agent_intent_analysis
from web_ui.intent_to_payload import build_analyze_raw_form_from_intent
from web_ui.rental_intent import AgentRentalRequest
from web_ui.rental_intent_parser import intent_has_key_signals, parse_rental_intent
from web_ui.result_ui import section_header

P5_KEY_NL = "p5_agent_nl_input"
P5_KEY_INTENT = "p5_agent_last_intent"
P5_KEY_HINT = "p5_agent_form_hint"


def init_p5_agent_session(st: Any) -> None:
    if P5_KEY_PHASE not in st.session_state:
        st.session_state[P5_KEY_PHASE] = PHASE_IDLE


def _consume_parsing(st: Any) -> None:
    """parsing → parsed（规则解析，无 LLM）。"""
    if st.session_state.get(P5_KEY_PHASE) != PHASE_PARSING:
        return
    raw = st.session_state.get(P5_KEY_NL, "")
    if not isinstance(raw, str):
        raw = str(raw) if raw is not None else ""
    intent = parse_rental_intent(raw)
    st.session_state[P5_KEY_INTENT] = intent.to_dict()
    st.session_state[P5_KEY_PHASE] = PHASE_PARSED


def _process_agent_batch_submit(
    st: Any,
    *,
    lab: dict[str, str],
    use_local: bool,
    api_base_url: str,
    limit_per_source: int,
    headless: bool,
    persist_listings: bool,
    async_mode: bool = False,
) -> None:
    """Continue to Analysis → submitting → analysis_*（P7：真实多平台 + batch）。"""
    if st.session_state.get(P5_KEY_PHASE) != PHASE_SUBMITTING:
        return
    it = AgentRentalRequest.from_dict(st.session_state.get(P5_KEY_INTENT) or {})

    if async_mode:
        _status_box = st.empty()
        _status_box.info("Submitting async task to backend…")

        def _on_status(tid: str, status_text: str) -> None:
            _status_box.info("Task **%s** — %s" % (tid, status_text))

        resp, err, payload = run_agent_intent_analysis(
            it,
            use_local=use_local,
            api_base_url=api_base_url,
            limit_per_source=limit_per_source,
            headless=headless,
            persist_listings=persist_listings,
            async_mode=True,
            on_status=_on_status,
        )
    else:
        with st.spinner(lab.get("p5_agent_spinner_submit", "Running batch analysis…")):
            resp, err, payload = run_agent_intent_analysis(
                it,
                use_local=use_local,
                api_base_url=api_base_url,
                limit_per_source=limit_per_source,
                headless=headless,
                persist_listings=persist_listings,
            )
    if resp is None:
        st.session_state[P5_KEY_PHASE] = PHASE_ANALYSIS_ERROR
        st.session_state["p5_agent_last_error"] = err or "Unknown error"
        st.session_state["p2_batch_last"] = {
            "success": False,
            "error": {"message": err or "Unknown error"},
        }
        return
    st.session_state["p2_batch_last"] = resp
    st.session_state["p2_batch_last_request"] = payload
    if isinstance(payload, dict) and payload.get("_p7_debug"):
        st.session_state["p7_last_debug"] = payload["_p7_debug"]
    if err:
        st.session_state["p7_last_transport_note"] = err
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


def apply_agent_intent_to_form_keys(
    intent: AgentRentalRequest,
    form_keys: dict[str, str],
    st_session: Any,
) -> list[str]:
    """将 intent 转为与 analyze-batch 单条 property 一致的数值，并写入表单 session。"""
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
    limit_per_source: int = 10,
    headless: bool = True,
    persist_listings: bool = True,
    async_mode: bool = False,
) -> None:
    """
    顺序：1) 输入 2) Parse 3) 预览 4) Continue to Analysis 5) 状态提示。
    **Continue** 触发 P7 真实多平台抓取 + analyze-batch；结果写入 `p2_batch_last`，与下方 Batch 区共用。
    """
    init_p5_agent_session(st)
    migrate_agent_phase(st.session_state)

    if st.session_state.pop("p5_refinement_parse_reminder", False):
        st.info(lab.get("p5_agent_refine_parse_reminder", ""))
    if st.session_state.pop("p5_refinement_snippet_added", False):
        st.success(lab.get("p5_refinement_snippet_ok", ""))

    _ph0 = st.session_state.get(P5_KEY_PHASE)
    if _ph0 == PHASE_PARSING:
        st.info(lab.get("p5_agent_status_parsing", ""))
    if _ph0 == PHASE_SUBMITTING:
        st.info(lab.get("p5_agent_status_submitting", ""))

    _consume_parsing(st)
    _process_agent_batch_submit(
        st,
        lab=lab,
        use_local=use_local,
        api_base_url=api_base_url,
        limit_per_source=limit_per_source,
        headless=headless,
        persist_listings=persist_listings,
        async_mode=async_mode,
    )

    migrate_agent_phase(st.session_state)
    phase = st.session_state.get(P5_KEY_PHASE, PHASE_IDLE)

    section_header(
        st,
        lab["p5_agent_section_title"],
        level=3,
        caption=lab["p5_agent_section_caption"],
    )

    _intent_for_caption = AgentRentalRequest.from_dict(
        st.session_state.get(P5_KEY_INTENT) or {}
    )
    st.caption(
        "%s %s"
        % (
            lab.get("p5_agent_current_step_label", "Current step:"),
            format_agent_phase_caption(phase, lab, intent=_intent_for_caption),
        )
    )

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
            st.session_state[P5_KEY_PHASE] = PHASE_PARSING

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
        PHASE_PARSED,
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
        _refine = agent_refinement_available(_it)

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

        if _refine and phase == PHASE_PARSED:
            st.caption(lab.get("p5_agent_refinement_hint_before_run", ""))

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
