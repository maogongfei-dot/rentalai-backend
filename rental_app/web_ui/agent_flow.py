# P5 Phase5: Agent 流程状态单一来源（轻量，无状态机库）
from __future__ import annotations

from typing import Any

from web_ui.agent_refinement import get_refinement_suggestions
from web_ui.rental_intent import AgentRentalRequest

P5_KEY_PHASE = "p5_agent_phase"

# 与验收文档一致的标准 phase 值
PHASE_IDLE = "idle"
PHASE_PARSING = "parsing"
PHASE_PARSED = "parsed"
PHASE_READY_FOR_ANALYSIS = "ready_for_analysis"
PHASE_SUBMITTING = "submitting"
PHASE_ANALYSIS_SUCCESS = "analysis_success"
PHASE_ANALYSIS_ERROR = "analysis_error"

# Phase1–4 旧值迁移（避免用户 session 卡住）
_LEGACY_PHASE_MAP: dict[str, str] = {
    "parsing_preview": PHASE_PARSING,
    "parsed_result": PHASE_PARSED,
}


def migrate_agent_phase(session_state: Any) -> None:
    p = session_state.get(P5_KEY_PHASE)
    if isinstance(p, str) and p in _LEGACY_PHASE_MAP:
        session_state[P5_KEY_PHASE] = _LEGACY_PHASE_MAP[p]


def agent_refinement_available(intent: AgentRentalRequest) -> bool:
    """是否仍有可展示的补充建议（用于 caption 后缀，非独立存储 phase）。"""
    return len(get_refinement_suggestions(intent)) > 0


def format_agent_phase_caption(
    phase: str,
    lab: dict[str, str],
    *,
    intent: AgentRentalRequest | None = None,
) -> str:
    """页顶一行：当前阶段人话说明 + 可选 refinement 提示。"""
    key = "p5_agent_phase_ui_%s" % phase
    line = lab.get(key)
    if not line:
        fb = lab.get("p5_agent_phase_ui_fallback", "Step: **%s**")
        try:
            line = fb % phase.replace("_", " ")
        except TypeError:
            line = "Step: **%s**" % phase.replace("_", " ")
    suf = (lab.get("p5_agent_refinement_available_suffix") or "").strip()
    if (
        intent is not None
        and suf
        and agent_refinement_available(intent)
        and phase in (PHASE_PARSED, PHASE_ANALYSIS_SUCCESS, PHASE_ANALYSIS_ERROR)
    ):
        line = "%s %s" % (line.rstrip(), suf)
    return line.strip()
