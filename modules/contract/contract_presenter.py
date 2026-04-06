"""
Contract analysis console presentation: envelope from ``run_contract_analysis`` (Phase 3 Part 25).
"""

from __future__ import annotations

from typing import Any


def format_contract_result_text(final_output: dict[str, Any]) -> str:
    """
    Build a multi-line text block for the full contract envelope (module, verdict, risk, lists).
    """
    lines: list[str] = ["=== Contract Analysis Result ==="]
    lines.append(f"Module: {final_output.get('module')}")
    lines.append(f"OK: {final_output.get('ok')}")
    verdict = final_output.get("verdict")
    if verdict:
        lines.append(f"Verdict status: {verdict.get('status')}")
        lines.append(f"Verdict title: {verdict.get('title')}")
        lines.append(f"Verdict message: {verdict.get('message')}")
    if final_output.get("ok"):
        summary = final_output.get("summary") or {}
        if not isinstance(summary, dict):
            summary = {}
        lines.append(f"Risk level: {summary.get('risk_level')}")
        lines.append(f"Explanation: {summary.get('overall_explanation')}")
        lines.append("Actions:")
        for action in final_output.get("actions") or []:
            lines.append(f"- {action}")
        lines.append("Missing clauses:")
        missing = final_output.get("missing_clauses")
        if missing:
            for item in missing:
                lines.append(f"- {item}")
        else:
            lines.append("- None detected")
        lines.append("Flagged clauses:")
        flagged = final_output.get("flagged_clauses")
        if flagged:
            for item in flagged:
                lines.append(f"- {item}")
        else:
            lines.append("- None detected")
    else:
        lines.append(f"Error: {final_output.get('error')}")
    return "\n".join(lines)


def print_contract_result(final_output: dict[str, Any]) -> None:
    """Print ``run_contract_analysis`` envelope (module, verdict, risk, actions, locators)."""
    print(format_contract_result_text(final_output))
