"""
Contract analysis runtime: normalize input, format pipeline output, actions, locators, verdict, envelope.

Phase 3 Part 23 — sits between ``analyze_contract`` (contract_api) and CLI / tests.
"""

from __future__ import annotations

import re
from typing import Any

from modules.contract.contract_api import analyze_contract

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
