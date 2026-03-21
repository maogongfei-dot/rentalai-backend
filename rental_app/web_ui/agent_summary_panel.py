# P5 Phase4：Agent Summary + Refine Your Search（Streamlit，非聊天）
from __future__ import annotations

from typing import Any

from web_ui.agent_refinement import RefinementSuggestion, get_refinement_suggestions
from web_ui.rental_intent import AgentRentalRequest
from web_ui.result_ui import section_header

# 与 agent_entry 中文本框 key 一致
P5_AGENT_NL_WIDGET_KEY = "p5_agent_nl_input"


def _append_nl_snippet(st_session: Any, snippet: str) -> None:
    cur = st_session.get(P5_AGENT_NL_WIDGET_KEY, "")
    if not isinstance(cur, str):
        cur = ""
    snippet = (snippet or "").strip()
    if not snippet:
        return
    st_session[P5_AGENT_NL_WIDGET_KEY] = ("%s\n%s" % (cur, snippet)).strip() if cur else snippet
    st_session["p5_refinement_snippet_added"] = True


def render_agent_insight_panel(
    st: Any,
    *,
    lab: dict[str, str],
    bundle: dict[str, Any],
    intent: AgentRentalRequest,
    key_prefix: str,
) -> None:
    """分析结果之后：Agent summary + Refine Your Search（追加 NL 片段）。"""
    section_header(
        st,
        lab["p5_agent_insight_title"],
        level=4,
        caption=lab.get("p5_agent_insight_caption", ""),
    )

    st.markdown("### %s" % bundle.get("headline", "Overview"))
    ss = bundle.get("short_summary") or ""
    if ss:
        st.markdown(ss)

    ib = bundle.get("insight_bullets") or []
    if ib:
        st.markdown("**What drove this view**")
        for line in ib:
            st.markdown("- %s" % line)

    ci = bundle.get("caution_items") or []
    for line in ci:
        st.warning(line)

    sugg: list[RefinementSuggestion] = get_refinement_suggestions(intent)
    if not sugg:
        st.caption(lab.get("p5_agent_refine_none", "Core preferences look specified — tweak NL or form if you want to iterate."))
        return

    with st.expander(lab["p5_agent_refine_title"], expanded=False):
        st.caption(lab["p5_agent_refine_caption"])
        for s in sugg:
            st.markdown("- **%s** — %s" % (s.button_label, s.question))

        st.markdown(lab.get("p5_agent_refine_quick_actions_blurb", ""))
        for s in sugg:

            def _make_append_cb(snippet: str):
                def _cb() -> None:
                    _append_nl_snippet(st.session_state, snippet)

                return _cb

            q, b = st.columns([3, 1])
            with q:
                st.caption(s.question)
            with b:
                st.button(
                    s.button_label,
                    key="%s_refine_%s" % (key_prefix, s.field_id),
                    on_click=_make_append_cb(s.nl_snippet),
                    type="secondary",
                )

        def _remind_parse() -> None:
            st.session_state["p5_refinement_parse_reminder"] = True

        st.button(
            lab.get("p5_agent_refine_jump_parse", "Remind me to Parse"),
            key="%s_refine_hint" % key_prefix,
            type="primary",
            help=lab.get("p5_agent_refine_jump_help", ""),
            on_click=_remind_parse,
        )
