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

    followup_questions = final_result.get("followup_questions")
    if isinstance(followup_questions, list) and followup_questions:
        lines.append("你还可以继续确认：")
        for item in followup_questions:
            text = str(item).strip()
            if text:
                lines.append(f"- {text}")
        lines.append("")

    missing_info_items = final_result.get("missing_info_items")
    if isinstance(missing_info_items, list) and missing_info_items:
        lines.append("当前还缺：")
        for item in missing_info_items:
            text = str(item).strip()
            if text:
                lines.append(f"- {text}")
        lines.append("")

    decision_result = final_result.get("decision_result")
    if isinstance(decision_result, dict) and decision_result:
        lines.append("最终判断：")
        label = str(decision_result.get("label") or "").strip()
        reason = str(decision_result.get("reason") or "").strip()
        confidence = str(decision_result.get("confidence") or "").strip()
        action_hint = str(decision_result.get("action_hint") or "").strip()
        lines.append(f"- 状态：{label}")
        lines.append(f"- 原因：{reason}")
        lines.append(f"- 置信度：{confidence}")
        lines.append(f"- 行动提示：{action_hint}")
        lines.append("")

    cleaned_lines = _trim_trailing_blank_lines(lines)
    return "\n".join(cleaned_lines).strip()


def _trim_trailing_blank_lines(lines: List[str]) -> List[str]:
    result = list(lines)
    while result and result[-1] == "":
        result.pop()
    return result
