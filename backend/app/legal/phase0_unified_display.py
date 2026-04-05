"""
Phase 0 unified display envelope (presentation only; no rule-engine changes).

Produces a stable JSON shape and a plain-text block for CLI / future AI layers.
"""

from __future__ import annotations

from typing import Any

from .compliance_types import ComplianceAnalysisResult, RuleEvaluation

# --- risk badge (emoji + label) -------------------------------------------------

_HIGH_ALIASES = frozenset({"high", "critical", "severe", "danger"})
_MEDIUM_ALIASES = frozenset({"medium", "warning", "moderate"})
_LOW_ALIASES = frozenset({"low", "safe", "ok", "good"})


def normalize_raw_risk_level(raw: str | None) -> str:
    """Map arbitrary severity strings to high | medium | low | unknown."""
    if raw is None:
        return "unknown"
    s = str(raw).strip().lower()
    if not s:
        return "unknown"
    if s in _HIGH_ALIASES or "high" in s or "critical" in s or "severe" in s:
        return "high"
    if s in _MEDIUM_ALIASES or "medium" in s or "warn" in s:
        return "medium"
    if s in _LOW_ALIASES or s == "low" or s.endswith(" low") or s.startswith("low "):
        return "low"
    return "unknown"


def build_risk_badge(raw_level: str) -> str:
    rl = normalize_raw_risk_level(raw_level)
    if rl == "high":
        return "❌ High Risk"
    if rl == "medium":
        return "⚠️ Medium Risk"
    if rl == "low":
        return "✅ Low Risk"
    return "⚠️ Needs review"


def _collect_key_reasons(result: ComplianceAnalysisResult) -> list[str]:
    reasons: list[str] = []
    sp = (result.summary_plain or "").strip()
    if sp:
        reasons.append(sp)
    for rule in result.rule_results:
        if rule.risk_level in ("high", "medium") and (rule.explanation_plain or "").strip():
            t = rule.explanation_plain.strip()
            if t not in reasons:
                reasons.append(t)
    for rule in result.rule_results:
        for rf in rule.matched_red_flags:
            line = f"Flag: {rf.strip()}"
            if line not in reasons:
                reasons.append(line)
    return reasons


def _collect_legal_basis(result: ComplianceAnalysisResult) -> list[str]:
    basis: list[str] = []
    for rule in result.rule_results:
        title = (rule.title or "").strip()
        if title:
            basis.append(f"{title} (ruleset baseline)")
        for kp in rule.matched_key_points:
            k = (kp or "").strip()
            if k and k not in basis:
                basis.append(k)
    return basis


def _collect_recommended_actions(result: ComplianceAnalysisResult, raw_level: str) -> list[str]:
    actions: list[str] = []
    if raw_level == "high":
        actions.append(
            "Seek independent legal or housing advice before relying on this wording."
        )
    elif raw_level == "medium":
        actions.append(
            "Review flagged items carefully and consider professional advice if unsure."
        )
    else:
        actions.append("Keep a copy of the tenancy agreement and monitor any changes.")
    if any(rule.matched_red_flags for rule in result.rule_results):
        actions.append("Address any matched red-flag patterns before signing.")
    actions.append("Use this screen as a guide only — it is not legal advice.")
    return actions


def build_phase0_unified_from_compliance_result(
    result: ComplianceAnalysisResult,
) -> dict[str, Any]:
    """Build the canonical Phase 0 display dict from a compliance engine result."""
    raw_level = normalize_raw_risk_level(result.overall_risk_level)
    return {
        "summary": (result.summary_plain or "").strip(),
        "risk_badge": build_risk_badge(raw_level),
        "key_reasons": _collect_key_reasons(result),
        "legal_basis": _collect_legal_basis(result),
        "recommended_actions": _collect_recommended_actions(result, raw_level),
        "raw_level": raw_level,
    }


def build_phase0_unified_from_legal_response(legal_response: dict[str, Any]) -> dict[str, Any]:
    """Build Phase 0 display from an API-shaped ``legal_compliance`` dict (no dataclass)."""
    overall = legal_response.get("overall") if isinstance(legal_response.get("overall"), dict) else {}
    summary = str(overall.get("summary_plain") or "").strip()
    risk_label = str(overall.get("overall_risk_level") or "")
    raw_level = normalize_raw_risk_level(risk_label)
    rules = legal_response.get("rules")
    if not isinstance(rules, list):
        rules = []

    key_reasons: list[str] = []
    if summary:
        key_reasons.append(summary)
    for item in rules:
        if not isinstance(item, dict):
            continue
        rl = str(item.get("risk_level") or "").lower()
        if "high" in rl or "medium" in rl:
            ex = str(item.get("explanation_plain") or "").strip()
            if ex and ex not in key_reasons:
                key_reasons.append(ex)
        for rf in item.get("matched_red_flags") or []:
            line = f"Flag: {str(rf).strip()}"
            if line not in key_reasons:
                key_reasons.append(line)

    legal_basis: list[str] = []
    for item in rules:
        if not isinstance(item, dict):
            continue
        t = str(item.get("title") or "").strip()
        if t:
            legal_basis.append(f"{t} (ruleset baseline)")
        for kp in item.get("matched_key_points") or []:
            k = str(kp).strip()
            if k and k not in legal_basis:
                legal_basis.append(k)

    meta = legal_response.get("meta") if isinstance(legal_response.get("meta"), dict) else {}
    tmp = ComplianceAnalysisResult(
        jurisdiction=str(meta.get("jurisdiction") or "england"),
        target_date=None,
        source_type="contract_clause",
        overall_is_legal=None,
        overall_risk_level=risk_label or raw_level,
        summary_plain=summary,
        disclaimer=str(overall.get("disclaimer") or ""),
        rule_results=[],
    )
    recommended_actions = _collect_recommended_actions(tmp, raw_level)

    return {
        "summary": summary,
        "risk_badge": build_risk_badge(raw_level),
        "key_reasons": key_reasons,
        "legal_basis": legal_basis,
        "recommended_actions": recommended_actions,
        "raw_level": raw_level,
    }


def format_phase0_display_text(display: dict[str, Any]) -> str:
    """Plain-text block for CLI / logs; safe with empty lists."""
    summary = str(display.get("summary") or "").strip()
    badge = str(display.get("risk_badge") or build_risk_badge(str(display.get("raw_level") or "")))
    key_reasons = display.get("key_reasons")
    legal_basis = display.get("legal_basis")
    recommended_actions = display.get("recommended_actions")
    if not isinstance(key_reasons, list):
        key_reasons = []
    if not isinstance(legal_basis, list):
        legal_basis = []
    if not isinstance(recommended_actions, list):
        recommended_actions = []

    lines: list[str] = []
    lines.append("【Conclusion】")
    lines.append(badge)
    if summary:
        lines.append(summary)
    lines.append("")
    lines.append("【Key Reasons】")
    if key_reasons:
        for r in key_reasons:
            lines.append(f"- {str(r).strip()}")
    else:
        lines.append("- (none)")
    lines.append("")
    lines.append("【Legal Basis】")
    if legal_basis:
        for b in legal_basis:
            lines.append(f"- {str(b).strip()}")
    else:
        lines.append("- (none)")
    lines.append("")
    lines.append("【Recommended Actions】")
    if recommended_actions:
        for i, a in enumerate(recommended_actions, start=1):
            lines.append(f"{i}. {str(a).strip()}")
    else:
        lines.append("1. (none)")
    return "\n".join(lines).strip() + "\n"
