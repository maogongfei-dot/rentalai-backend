"""
Phase 0 natural-language presentation layer (readability only; no rule changes).

Consumes ``phase0_unified`` dicts from :mod:`phase0_unified_display`.
"""

from __future__ import annotations

import re
from typing import Any

from .phase0_unified_display import build_risk_badge, normalize_raw_risk_level


def _safe_list(val: Any) -> list[str]:
    if not isinstance(val, list):
        return []
    return [str(x).strip() for x in val if str(x).strip()]


def _opening_sentence(raw_level: str) -> str:
    if raw_level == "high":
        return (
            "This contract looks high risk and should be reviewed carefully before signing."
        )
    if raw_level == "medium":
        return (
            "This issue appears manageable, but there are still some important points to check."
        )
    if raw_level == "low":
        return (
            "Based on this pass, nothing major stood out, but a quick double-check is still sensible."
        )
    return (
        "We could not confidently classify the risk level from this text alone; treat it as needing review."
    )


def _humanize_flag_or_line(line: str) -> str:
    s = line.strip()
    if s.lower().startswith("flag:"):
        rest = s.split(":", 1)[-1].strip()
        if not rest:
            return "The screening flagged a concern in this area."
        return f"The screening highlights a concern: {rest}"
    return s


def _why_this_matters_sentences(
    raw_level: str,
    summary: str,
    key_reasons: list[str],
) -> list[str]:
    out: list[str] = []
    if summary:
        s = re.sub(r"\s+", " ", summary.strip())
        if raw_level == "high":
            out.append(f"The overall picture suggests meaningful exposure: {s}")
        elif raw_level == "medium":
            out.append(f"There is enough here to pause and verify: {s}")
        else:
            out.append(s)
    for kr in key_reasons:
        if not kr or (summary and kr.strip() == summary.strip()):
            continue
        out.append(_humanize_flag_or_line(kr))
        if len(out) >= 3:
            break
    if not out:
        if raw_level == "high":
            out.append(
                "The main worry is that unclear wording can create disputes or unexpected costs later."
            )
        elif raw_level == "medium":
            out.append(
                "Some clauses look incomplete or vague, which can cause friction if something goes wrong."
            )
        else:
            out.append(
                "The automated pass did not surface strong red flags, but tenancy wording still deserves a calm read-through."
            )
    return out[:3]


def _trim_reasons_for_bullets(items: list[str], max_items: int = 5) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for x in items:
        t = str(x).strip()
        if not t or t in seen:
            continue
        seen.add(t)
        out.append(t)
        if len(out) >= max_items:
            break
    return out


def _reassurance_block(raw_level: str) -> str:
    if raw_level == "high":
        return (
            "This does not automatically mean the tenancy is unsafe, but it is worth checking these points "
            "before moving forward. Avoid paying deposits or signing until you are comfortable with the wording."
        )
    if raw_level == "medium":
        return (
            "This does not automatically mean the tenancy is unsafe, but it is worth checking these points "
            "before moving forward. Take time to verify anything that feels unclear."
        )
    if raw_level == "low":
        return (
            "This does not automatically mean everything is perfect—tenancies always carry some paperwork risk. "
            "Keep your documents handy; you can revisit details later if you compare properties or bills."
        )
    return (
        "If you want, you can come back to this summary later when you compare another property or review related costs."
    )


def _actions_natural(actions: list[str], raw_level: str) -> list[str]:
    if not actions:
        if raw_level == "high":
            return [
                "Pause before you pay or sign anything you do not fully understand.",
                "Ask the landlord or agent to clarify flagged wording in writing if possible.",
            ]
        if raw_level == "medium":
            return [
                "Follow up on any unclear points before you commit.",
                "Keep a paper trail of what was agreed.",
            ]
        return [
            "No immediate action required, but keep the documents for reference.",
        ]
    out = []
    for i, a in enumerate(actions):
        t = str(a).strip()
        if not t:
            continue
        if i == 0 and raw_level == "high" and "sign" not in t.lower():
            out.append(f"{t} Do not rush payment or signature until you are satisfied.")
        else:
            out.append(t)
    return out if out else ["No immediate action required, but keep the documents for reference."]


def build_phase0_readable_report(phase0_unified: dict[str, Any]) -> str:
    """
    Turn a ``phase0_unified`` dict into a single user-facing narrative (English).

    Safe with empty lists; does not call the rule engine.
    """
    if not isinstance(phase0_unified, dict):
        phase0_unified = {}

    raw_level = normalize_raw_risk_level(str(phase0_unified.get("raw_level") or ""))
    summary = str(phase0_unified.get("summary") or "").strip()
    badge = str(phase0_unified.get("risk_badge") or "").strip() or build_risk_badge(raw_level)

    key_reasons = _safe_list(phase0_unified.get("key_reasons"))
    legal_basis = _safe_list(phase0_unified.get("legal_basis"))
    recommended_actions = _safe_list(phase0_unified.get("recommended_actions"))

    conclusion_line = _opening_sentence(raw_level)
    why_lines = _why_this_matters_sentences(raw_level, summary, key_reasons)
    bullets = _trim_reasons_for_bullets(key_reasons if key_reasons else [summary] if summary else [], 5)
    if not bullets:
        bullets = ["No major reasons were captured by this automated pass."]

    basis_lines = legal_basis[:] if legal_basis else []
    if not basis_lines:
        basis_lines = ["No specific legal reference identified."]

    actions = _actions_natural(recommended_actions, raw_level)

    lines: list[str] = []
    lines.append("【Conclusion】")
    lines.append(f"{badge}")
    lines.append(conclusion_line)
    lines.append("")
    lines.append("【Why This Matters】")
    for w in why_lines:
        lines.append(w)
    lines.append("")
    lines.append("【Key Reasons】")
    for b in bullets:
        lines.append(f"- {b}")
    lines.append("")
    lines.append("【Legal Basis】")
    for lb in basis_lines:
        lines.append(f"- {lb}")
    lines.append("")
    lines.append("【Recommended Actions】")
    for i, act in enumerate(actions, start=1):
        lines.append(f"{i}. {act}")
    lines.append("")
    lines.append("【Reassurance / Note】")
    lines.append(_reassurance_block(raw_level))
    return "\n".join(lines).strip() + "\n"
