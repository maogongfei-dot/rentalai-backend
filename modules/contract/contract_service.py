"""
Contract analysis runtime: normalize input, format pipeline output, actions, locators, verdict, envelope.

Phase 3 Part 23 — sits between ``analyze_contract`` (contract_api) and CLI / tests.
"""

from __future__ import annotations

import re
from typing import Any

from modules.contract.contract_api import analyze_contract
from modules.contract.contract_presenter import (
    build_analysis_completeness,
    build_blocking_factors,
    build_confidence_reason,
    build_direct_answer,
    build_direct_answer_short,
    build_final_display,
    build_human_confidence_notice,
    build_human_decision_factors_notice,
    build_human_missing_info_guidance,
    build_human_urgency_notice,
    build_key_decision_drivers,
    build_missing_information,
    build_priority_actions,
    build_recommended_decision,
    build_result_confidence,
    build_supporting_factors,
    build_urgency_level,
    build_urgency_reason,
)

from modules.contract.timeline_action_plan import (
    build_action_timeline,
    build_timeline_reason,
    build_human_timeline_notice,
)

# Phase 3 Part 11 — standardized envelope ``module`` field
CONTRACT_MODULE_NAME = "contract"

_DEFAULT_DETAIL = "No additional details available."


def _safe_str(value: Any, default: str = _DEFAULT_DETAIL) -> str:
    if value is None:
        return default
    s = str(value).strip()
    return s if s else default


def normalize_contract_input(text: str | None) -> str:
    """
    Minimal whitespace normalization before contract pipeline (no NLP, no translation).

    ``None`` → ``""``; strip ends; collapse runs of whitespace to a single space.
    """
    if text is None:
        return ""
    s = str(text).strip()
    if not s:
        return ""
    return re.sub(r"\s+", " ", s)


def format_contract_output(result: dict[str, Any]) -> dict[str, Any]:
    """
    Map ``analyze_contract`` return value to a stable shape for UI / chat (Phase 3 Part 11).
    """
    if not isinstance(result, dict):
        return {
            "ok": False,
            "module": CONTRACT_MODULE_NAME,
            "summary": None,
            "details": None,
            "error": "invalid result",
        }
    if not result.get("ok"):
        return {
            "ok": False,
            "module": CONTRACT_MODULE_NAME,
            "summary": None,
            "details": None,
            "error": _safe_str(result.get("error"), "Unknown error"),
        }
    data = result.get("data")
    if not isinstance(data, dict):
        data = {}
    risk = data.get("risk")
    if not isinstance(risk, dict):
        risk = {}
    expl = data.get("explanations")
    if not isinstance(expl, dict):
        expl = {}
    # Phase 4 Part 2 — mirror ``result["data"]["explanations"]["human_explanation"]`` into summary
    human_explanation = expl.get("human_explanation")
    return {
        "ok": True,
        "module": CONTRACT_MODULE_NAME,
        "summary": {
            "risk_level": risk.get("risk_level"),
            "overall_explanation": expl.get("overall_explanation"),
            "human_explanation": human_explanation,
        },
        "details": {
            "parsed": data.get("parsed"),
            "risk": data.get("risk"),
            "explanations": data.get("explanations"),
        },
        "error": None,
    }


def build_contract_actions(formatted_result: dict[str, Any]) -> list[str]:
    """Rule-based next-step suggestions from ``format_contract_output`` (Phase 3 Part 12)."""
    if not formatted_result.get("ok"):
        return [
            "Review the input contract text.",
            "Try again with a clearer or longer contract section.",
        ]
    summary = formatted_result.get("summary")
    if not isinstance(summary, dict):
        summary = {}
    level = summary.get("risk_level")
    if level == "high":
        return [
            "Review this contract carefully before signing.",
            "Check the flagged clauses in detail.",
            "Consider asking the landlord or agent for clarification.",
            "Consider getting legal or housing advice before proceeding.",
        ]
    if level == "medium":
        return [
            "Review the risky clauses carefully.",
            "Ask follow-up questions about unclear terms.",
            "Compare this contract with standard tenancy terms.",
        ]
    if level == "low":
        return [
            "No major risk detected, but review the contract carefully.",
            "Double-check rent, deposit, notice, and fee terms before signing.",
        ]
    return [
        "Review the contract result manually.",
        "Check the explanation and risk details carefully.",
    ]


def detect_missing_contract_clauses(text: str) -> list[str]:
    """
    Simple substring checks on normalized text (lowercase) for common tenancy topics.

    Phase 3 Part 13 — not legal advice; flags possible gaps only.
    """
    low = str(text).lower() if text else ""
    missing: list[str] = []
    if "deposit" not in low:
        missing.append("Missing deposit clause")
    if "notice" not in low:
        missing.append("Missing notice clause")
    if "rent" not in low:
        missing.append("Missing rent clause")
    if "repair" not in low and "maintenance" not in low:
        missing.append("Missing repair or maintenance clause")
    if "termination" not in low and "end of tenancy" not in low:
        missing.append("Missing termination or end of tenancy clause")
    if "fee" not in low:
        missing.append("Missing fees clause")
    return missing


_FLAGGED_CLAUSE_KEYWORDS: tuple[str, ...] = (
    "non-refundable",
    "fee",
    "fees",
    "penalty",
    "increase rent",
    "rent increase",
    "deduct",
    "deduction",
    "terminate",
    "termination",
    "without notice",
    "notice",
    "landlord may",
    "tenant must",
    "liable",
    "immediately",
)


def extract_flagged_clauses(text: str) -> list[str]:
    """
    Split normalized text on ``.``, ``;``, or newlines; keep segments whose lowercased
    text contains any risk keyword (Phase 3 Part 14).
    """
    if not text or not str(text).strip():
        return []
    parts = re.split(r"[.;\n]+", str(text))
    seen: set[str] = set()
    out: list[str] = []
    for p in parts:
        s = p.strip()
        if not s:
            continue
        low = s.lower()
        if any(kw in low for kw in _FLAGGED_CLAUSE_KEYWORDS):
            if s not in seen:
                seen.add(s)
                out.append(s)
    return out


def build_contract_verdict(final_output: dict[str, Any]) -> dict[str, str]:
    """
    Single headline conclusion from risk level, missing clauses, and flagged segments (Phase 3 Part 15).
    """
    if not final_output.get("ok"):
        return {
            "status": "error",
            "title": "We could not analyze this contract",
            "message": (
                "The contract text could not be analyzed clearly. Please check the input and "
                "try again with a clearer clause or a longer section."
            ),
        }
    summary = final_output.get("summary")
    if not isinstance(summary, dict):
        summary = {}
    risk_level = summary.get("risk_level")
    missing_clauses = final_output.get("missing_clauses") or []
    if not isinstance(missing_clauses, list):
        missing_clauses = []
    flagged_clauses = final_output.get("flagged_clauses") or []
    if not isinstance(flagged_clauses, list):
        flagged_clauses = []

    if risk_level == "high":
        return {
            "status": "high_risk",
            "title": "This contract needs careful review",
            "message": (
                "Some terms in this contract look high risk. You should review the flagged "
                "clauses carefully before signing anything."
            ),
        }
    if risk_level == "medium":
        return {
            "status": "review_needed",
            "title": "This contract may need clarification",
            "message": (
                "Some parts of this contract look unclear or potentially risky. It would be "
                "safer to review those clauses before you proceed."
            ),
        }
    if risk_level == "low":
        if len(missing_clauses) >= 3 or len(flagged_clauses) >= 2:
            return {
                "status": "review_needed",
                "title": "This contract looks lower risk, but still needs review",
                "message": (
                    "The overall risk looks lower, but some important terms may be missing or "
                    "unclear. It is still worth checking the details carefully."
                ),
            }
        return {
            "status": "acceptable_with_review",
            "title": "This contract looks generally acceptable",
            "message": (
                "No major risk was detected in this contract, but you should still review the "
                "key terms before signing."
            ),
        }
    return {
        "status": "manual_review",
        "title": "This contract needs manual review",
        "message": (
            "The result is not fully clear yet. Please review the explanation, flagged clauses, "
            "and missing terms carefully."
        ),
    }


# --- Phase 4 Part 4 — humanized next steps / evidence / risk warning (rule-based, Chinese) ---

_ACTION_SOURCE_KEYS: tuple[str, ...] = (
    "actions",
    "recommended_actions",
    "suggested_actions",
    "next_steps",
    "action_plan",
)

_EVIDENCE_SOURCE_KEYS: tuple[str, ...] = (
    "evidence",
    "required_evidence",
    "evidence_list",
    "proof",
    "proof_items",
    "proof_hints",
    "documents_needed",
)

# English action lines from ``build_contract_actions`` → natural Chinese steps
_EN_ACTION_TO_ZH: dict[str, str] = {
    "Review the input contract text.": "先把合同原文或相关条款整理清楚，再重新提交分析。",
    "Try again with a clearer or longer contract section.": "请再试一次，尽量粘贴更清晰或更长的条款段落。",
    "Review this contract carefully before signing.": "签字前请把整份合同和重要条款逐条核对清楚。",
    "Check the flagged clauses in detail.": "请重点核对系统标出的条款，确认你能接受再签字。",
    "Consider asking the landlord or agent for clarification.": "如有不清楚的地方，先向房东或中介要书面说明或补充条款。",
    "Consider getting legal or housing advice before proceeding.": "若条款影响较大，可先咨询租房或法律方面的专业意见。",
    "Review the risky clauses carefully.": "请把看起来有风险或含糊的条款先读透，再决定下一步。",
    "Ask follow-up questions about unclear terms.": "把疑问整理成几条具体问题，向对方书面确认并保留记录。",
    "Compare this contract with standard tenancy terms.": "可与常见标准租约条款对照，看是否有明显不合理之处。",
    "No major risk detected, but review the contract carefully.": "整体风险不高，但仍建议通读全文，重点看租金、押金与退租。",
    "Double-check rent, deposit, notice, and fee terms before signing.": "签字前请再核对租金、押金、通知期与各类费用约定。",
    "Review the contract result manually.": "请结合系统说明自行判断，必要时请他人协助阅读。",
    "Check the explanation and risk details carefully.": "请对照说明与风险细节逐项确认，不要只看结论。",
}


def _flatten_str_list(raw: Any, max_items: int = 8) -> list[str]:
    if not isinstance(raw, list):
        return []
    out: list[str] = []
    for x in raw:
        if isinstance(x, str) and x.strip():
            out.append(x.strip())
        elif isinstance(x, dict):
            for k in ("text", "message", "label", "title", "step"):
                t = x.get(k)
                if isinstance(t, str) and t.strip():
                    out.append(t.strip())
                    break
        if len(out) >= max_items:
            break
    return out


def _collect_action_lines(envelope: dict[str, Any]) -> list[str]:
    if not isinstance(envelope, dict):
        return []
    for key in _ACTION_SOURCE_KEYS:
        lines = _flatten_str_list(envelope.get(key))
        if lines:
            return lines
    summary = envelope.get("summary")
    if isinstance(summary, dict):
        for key in _ACTION_SOURCE_KEYS:
            lines = _flatten_str_list(summary.get(key))
            if lines:
                return lines
    details = envelope.get("details")
    if isinstance(details, dict):
        for key in _ACTION_SOURCE_KEYS:
            lines = _flatten_str_list(details.get(key))
            if lines:
                return lines
        risk = details.get("risk")
        if isinstance(risk, dict):
            for key in _ACTION_SOURCE_KEYS:
                lines = _flatten_str_list(risk.get(key))
                if lines:
                    return lines
    return []


def _collect_evidence_lines(envelope: dict[str, Any]) -> list[str]:
    if not isinstance(envelope, dict):
        return []
    for key in _EVIDENCE_SOURCE_KEYS:
        lines = _flatten_str_list(envelope.get(key))
        if lines:
            return lines
    summary = envelope.get("summary")
    if isinstance(summary, dict):
        for key in _EVIDENCE_SOURCE_KEYS:
            lines = _flatten_str_list(summary.get(key))
            if lines:
                return lines
    details = envelope.get("details")
    if isinstance(details, dict):
        for key in _EVIDENCE_SOURCE_KEYS:
            lines = _flatten_str_list(details.get(key))
            if lines:
                return lines
    return []


def _zh_from_missing_flagged(envelope: dict[str, Any]) -> list[str]:
    """Heuristic checklist when no explicit evidence list exists."""
    out: list[str] = []
    missing = envelope.get("missing_clauses") or []
    flagged = envelope.get("flagged_clauses") or []
    if not isinstance(missing, list):
        missing = []
    if not isinstance(flagged, list):
        flagged = []
    mlow = " ".join(str(x).lower() for x in missing)
    if "deposit" in mlow or any("deposit" in str(x).lower() for x in missing):
        out.append("租金、押金或相关付款记录（转账备注、收据或账单截图）。")
    if "rent" in mlow:
        out.append("租金标准与支付方式的约定（合同条款或补充说明）。")
    if "notice" in mlow or "termination" in mlow:
        out.append("与通知、解约或期限相关的往来记录或书面材料。")
    if "repair" in mlow or "maintenance" in mlow:
        out.append("房屋状况、维修或损坏相关的照片、视频或报修记录。")
    if flagged:
        out.append("与对方沟通过程中的聊天记录、邮件或书面往来（若有）。")
    return out


def build_human_next_steps(system_result: dict[str, Any]) -> list[str]:
    """
    Turn existing action suggestions into short Chinese steps (Phase 4 Part 4).

    Safe on missing fields; returns at most five lines.
    """
    if not isinstance(system_result, dict):
        return []
    raw = _collect_action_lines(system_result)
    if not raw:
        return []
    seen: set[str] = set()
    zh_lines: list[str] = []
    for s in raw[:8]:
        key = s.strip()
        line = _EN_ACTION_TO_ZH.get(key)
        if line is None:
            if any("\u4e00" <= c <= "\u9fff" for c in key):
                line = key
            else:
                line = f"建议你：{key[:120]}{'…' if len(key) > 120 else ''}"
        if line and line not in seen:
            seen.add(line)
            zh_lines.append(line)
        if len(zh_lines) >= 5:
            break
    return zh_lines


def build_human_evidence_checklist(system_result: dict[str, Any]) -> list[str]:
    """
    Build a readable evidence checklist in Chinese; uses explicit lists if present (Phase 4 Part 4).
    """
    if not isinstance(system_result, dict):
        return []
    explicit = _collect_evidence_lines(system_result)
    out: list[str] = []
    if explicit:
        for s in explicit[:6]:
            if any("\u4e00" <= c <= "\u9fff" for c in s):
                out.append(s)
            else:
                out.append(f"与本次争议相关的材料：{s[:100]}{'…' if len(s) > 100 else ''}")
    else:
        out.append("合同原文或相关条款截图（纸质合同可拍照或扫描清晰版）。")
        out.extend(_zh_from_missing_flagged(system_result))
        if len(out) == 1:
            out.append("与房东或中介的聊天记录、邮件或书面往来（若有）。")
    seen: set[str] = set()
    deduped: list[str] = []
    for line in out:
        if line and line not in seen:
            seen.add(line)
            deduped.append(line)
        if len(deduped) >= 6:
            break
    return deduped


def build_human_risk_warning(system_result: dict[str, Any]) -> str:
    """
    Short Chinese risk reminder from verdict / risk level; empty string if nothing to say.
    """
    if not isinstance(system_result, dict):
        return ""
    ok = system_result.get("ok")
    if ok is False:
        err = system_result.get("error")
        if err:
            return "目前分析未成功完成。若涉及纠纷，建议先保存好合同与沟通记录，再重试或寻求协助。"
        return "请检查输入后再试。若情况紧急，建议先保留证据，不要仅凭口头承诺处理。"
    if ok is not True:
        return ""

    summary = system_result.get("summary")
    if not isinstance(summary, dict):
        summary = {}
    risk_level = summary.get("risk_level")
    severity = summary.get("severity")
    if severity is None:
        det = system_result.get("details")
        if isinstance(det, dict):
            rb = det.get("risk")
            if isinstance(rb, dict):
                severity = rb.get("severity")
    verdict = system_result.get("verdict") or {}
    if not isinstance(verdict, dict):
        verdict = {}
    vstatus = verdict.get("status")

    flagged = system_result.get("flagged_clauses") or []
    n_flag = len(flagged) if isinstance(flagged, list) else 0
    missing = system_result.get("missing_clauses") or []
    n_miss = len(missing) if isinstance(missing, list) else 0

    if vstatus == "high_risk" or risk_level == "high" or (
        isinstance(severity, str) and severity.lower() in ("high", "critical", "severe")
    ):
        return "从目前结果看，部分条款风险偏高，签署前务必先核对清楚，不要匆忙签字。"

    if risk_level == "medium":
        if n_miss >= 3 or n_flag >= 2:
            return "条款或材料不够完整时，后面扯皮会更被动，建议先把关键约定补齐或留痕。"
        return "部分表述可能不够清晰，建议先问明白再签字，避免日后争议。"

    if risk_level == "low":
        if vstatus == "review_needed":
            if n_miss >= 3 or n_flag >= 2:
                return "整体风险不算高，但仍有条款缺口或敏感表述，建议把细节核对完再决定。"
            return "整体风险不高，但仍有重要条款可能未写清，建议补问并留痕后再签字。"
        if vstatus == "acceptable_with_review":
            return "目前未发现特别突出的风险信号，但仍建议你通读全文并保留重要沟通记录。"

    if vstatus == "manual_review" or (
        risk_level is not None and risk_level not in ("high", "medium", "low")
    ):
        return "系统结论不够确定时，不建议仅凭本结果做最终决定，请结合材料再判断。"

    return ""


def build_contract_result(result: dict[str, Any], normalized_text: str) -> dict[str, Any]:
    """
    Single entry to assemble the contract analysis envelope (Phase 3 Part 16).

    Wraps ``format_contract_output``, actions, missing/flagged locators, and ``verdict``.
    """
    formatted_result = format_contract_output(result)
    actions = build_contract_actions(formatted_result)
    missing_clauses = detect_missing_contract_clauses(normalized_text)
    flagged_clauses = extract_flagged_clauses(normalized_text)
    draft_output: dict[str, Any] = {
        "ok": formatted_result.get("ok"),
        "module": CONTRACT_MODULE_NAME,
        "summary": formatted_result.get("summary"),
        "details": formatted_result.get("details"),
        "actions": actions,
        "missing_clauses": missing_clauses,
        "flagged_clauses": flagged_clauses,
        "verdict": None,
        "error": formatted_result.get("error"),
    }
    draft_output["verdict"] = build_contract_verdict(draft_output)
    draft_output["human_next_steps"] = build_human_next_steps(draft_output)
    draft_output["human_evidence_checklist"] = build_human_evidence_checklist(draft_output)
    draft_output["human_risk_warning"] = build_human_risk_warning(draft_output)
    draft_output["analysis_completeness"] = build_analysis_completeness(draft_output)
    draft_output["missing_information"] = build_missing_information(draft_output)
    draft_output["human_missing_info_guidance"] = build_human_missing_info_guidance(draft_output)
    draft_output["recommended_decision"] = build_recommended_decision(draft_output)
    draft_output["direct_answer"] = build_direct_answer(draft_output)
    draft_output["direct_answer_short"] = build_direct_answer_short(draft_output)
    draft_output["result_confidence"] = build_result_confidence(draft_output)
    draft_output["confidence_reason"] = build_confidence_reason(draft_output)
    draft_output["human_confidence_notice"] = build_human_confidence_notice(draft_output)
    draft_output["urgency_level"] = build_urgency_level(draft_output)
    draft_output["urgency_reason"] = build_urgency_reason(draft_output)
    draft_output["priority_actions"] = build_priority_actions(draft_output)
    draft_output["human_urgency_notice"] = build_human_urgency_notice(draft_output)
    draft_output["supporting_factors"] = build_supporting_factors(draft_output)
    draft_output["blocking_factors"] = build_blocking_factors(draft_output)
    draft_output["key_decision_drivers"] = build_key_decision_drivers(draft_output)
    draft_output["human_decision_factors_notice"] = build_human_decision_factors_notice(draft_output)
    draft_output["final_display"] = build_final_display(draft_output)
    return draft_output


def run_contract_analysis(text: str) -> dict[str, Any]:
    """
    Unified contract pipeline: normalize → ``analyze_contract`` → ``build_contract_result``.

    Empty or whitespace-only ``text`` follows the same path as before (normalize then analyze).
    """
    normalized_text = normalize_contract_input(text)
    result = analyze_contract(normalized_text)
    return build_contract_result(result, normalized_text)


def contract_normalized_text(text: str) -> str:
    """Normalized text for CLI banners (same rules as pipeline input)."""
    return normalize_contract_input(text)


def format_contract_result(formatted: dict[str, Any]) -> str:
    """
    Build a readable console block from ``format_contract_output`` (Phase 3 Part 7 / 11).

    On failure: Contract Analysis Result + OK + Error.
    On success: OK, risk level, overall explanation, optional risk list / counts / per-clause text.
    """
    lines: list[str] = ["Contract Analysis Result", ""]
    ok = formatted.get("ok")
    lines.append(f"OK: {ok}")
    if not formatted.get("ok"):
        err = formatted.get("error")
        lines.append(f"Error: {_safe_str(err, 'Unknown error')}")
        return "\n".join(lines)

    summary = formatted.get("summary") or {}
    if not isinstance(summary, dict):
        summary = {}
    lines.append(f"Risk level: {_safe_str(summary.get('risk_level'), 'none')}")
    lines.append(f"Explanation: {_safe_str(summary.get('overall_explanation'), _DEFAULT_DETAIL)}")
    lines.append(f"Human explanation: {summary.get('human_explanation')}")

    details = formatted.get("details") or {}
    if not isinstance(details, dict):
        details = {}
    risk = details.get("risk")
    if not isinstance(risk, dict):
        risk = {}
    expl = details.get("explanations")
    if not isinstance(expl, dict):
        expl = {}

    sm = risk.get("summary")
    if isinstance(sm, dict) and sm:
        lines.append("")
        lines.append("Summary counts:")
        for key in ("total_risks", "high_risks", "medium_risks", "low_risks"):
            if key in sm:
                lines.append(f"  {key}: {sm[key]}")

    risks = risk.get("risks")
    if isinstance(risks, list) and risks:
        lines.append("")
        lines.append("Flagged clauses (risk items):")
        for i, item in enumerate(risks, 1):
            if not isinstance(item, dict):
                continue
            t = _safe_str(item.get("type"), "?")
            lv = _safe_str(item.get("level"), "?")
            msg = _safe_str(item.get("message"), "")
            lines.append(f"  {i}. [{t}] {lv}: {msg}")

    rex = expl.get("risk_explanations")
    if isinstance(rex, list) and rex:
        lines.append("")
        lines.append("Recommendations / clause explanations:")
        for i, item in enumerate(rex, 1):
            if not isinstance(item, dict):
                continue
            t = _safe_str(item.get("type"), "?")
            ex = _safe_str(item.get("explanation"), "")
            lines.append(f"  {i}. ({t}) {ex}")

    return "\n".join(lines)


def print_contract_result(formatted: dict[str, Any]) -> None:
    """Print contract analysis from ``format_contract_output`` (section-banner style)."""
    print("======== CONTRACT ANALYSIS ========")
    print(format_contract_result(formatted))
    print("===================================")
