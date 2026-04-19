from typing import Any, Dict, List


def build_final_response_text(final_result: Dict[str, Any]) -> str:
    final_result = final_result or {}

    explain_result = final_result.get("explain_result")
    summary = final_result.get("summary")
    recommendation = final_result.get("recommendation")
    risks = final_result.get("risks") or []
    reasons = final_result.get("reasons") or []

    lines: List[str] = []

    if isinstance(explain_result, dict):
        explain_summary = str(explain_result.get("summary") or "").strip()
        explain_pros = explain_result.get("pros") or []
        explain_cons = explain_result.get("cons") or []
        explain_recommendation = str(explain_result.get("recommendation") or "").strip()

        if explain_summary:
            lines.append("总结：")
            lines.append(explain_summary)
            lines.append("")

        lines.append("优点：")
        if isinstance(explain_pros, list) and explain_pros:
            for item in explain_pros:
                text = str(item).strip()
                if text:
                    lines.append(f"- {text}")
        lines.append("")

        lines.append("需要注意：")
        if isinstance(explain_cons, list) and explain_cons:
            for item in explain_cons:
                text = str(item).strip()
                if text:
                    lines.append(f"- {text}")
        lines.append("")

        if explain_recommendation:
            lines.append("建议：")
            lines.append(explain_recommendation)
            lines.append("")

    if summary:
        lines.append("原始总结：")
        lines.append(str(summary).strip())
        lines.append("")

    if reasons:
        lines.append("原始 reasons：")
        for item in reasons:
            text = str(item).strip()
            if text:
                lines.append(f"- {text}")
        lines.append("")

    if risks:
        lines.append("原始 risks：")
        for item in risks:
            if isinstance(item, dict):
                title = str(item.get("title") or item.get("name") or item.get("risk") or item.get("issue") or "Unknown risk").strip()
                level = str(item.get("level") or item.get("severity") or item.get("risk_level") or "").strip()
                detail = str(item.get("detail") or item.get("description") or item.get("reason") or "").strip()

                risk_line = f"- {title}"
                if level:
                    risk_line += f" ({level})"
                if detail:
                    risk_line += f": {detail}"

                lines.append(risk_line)
            else:
                text = str(item).strip()
                if text:
                    lines.append(f"- {text}")
        lines.append("")

    if recommendation:
        lines.append("原始 recommendation：")
        lines.append(str(recommendation).strip())
        lines.append("")

    next_actions = final_result.get("next_actions")
    if isinstance(next_actions, list) and next_actions:
        lines.append("下一步建议：")
        for item in next_actions:
            text = str(item).strip()
            if text:
                lines.append(f"- {text}")
        lines.append("")

    cleaned_lines = _trim_trailing_blank_lines(lines)
    return "\n".join(cleaned_lines).strip()


def _trim_trailing_blank_lines(lines: List[str]) -> List[str]:
    result = list(lines)
    while result and result[-1] == "":
        result.pop()
    return result
