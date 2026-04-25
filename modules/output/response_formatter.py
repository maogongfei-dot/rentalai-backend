from typing import Any, Dict, List


def build_final_response_text(final_result: Dict[str, Any]) -> str:
    final_result = final_result or {}

    explain_result = final_result.get("explain_result")
    summary = final_result.get("summary")
    recommendation = final_result.get("recommendation")
    risks = final_result.get("risks") or []
    reasons = final_result.get("reasons") or []

    lines: List[str] = []
    section_added = False

    def append_text_section(title: str, content: Any) -> None:
        nonlocal section_added
        text = str(content or "").strip()
        if not text:
            return
        if section_added:
            lines.append("")
        lines.append(title)
        lines.append(text)
        section_added = True

    def append_list_section(title: str, items: Any) -> None:
        nonlocal section_added
        if not isinstance(items, list):
            return
        bullet_lines: List[str] = []
        for item in items:
            text = str(item).strip()
            if text:
                bullet_lines.append(f"- {text}")
        if not bullet_lines:
            return
        if section_added:
            lines.append("")
        lines.append(title)
        lines.extend(bullet_lines)
        section_added = True

    # 1) 最终判断（优先）
    decision_result = final_result.get("decision_result")
    if isinstance(decision_result, dict):
        decision_lines: List[str] = []
        label = str(decision_result.get("label") or "").strip()
        reason = str(decision_result.get("reason") or "").strip()
        confidence = str(decision_result.get("confidence") or "").strip()
        action_hint = str(decision_result.get("action_hint") or "").strip()
        if label:
            decision_lines.append(f"- 状态：{label}")
        if reason:
            decision_lines.append(f"- 原因：{reason}")
        if confidence:
            decision_lines.append(f"- 置信度：{confidence}")
        if action_hint:
            decision_lines.append(f"- 行动提示：{action_hint}")
        if decision_lines:
            lines.append("最终判断：")
            lines.extend(decision_lines)
            section_added = True

    if isinstance(explain_result, dict):
        explain_summary = str(explain_result.get("summary") or "").strip()
        explain_pros = explain_result.get("pros") or []
        explain_cons = explain_result.get("cons") or []
        explain_recommendation = str(explain_result.get("recommendation") or "").strip()
        append_text_section("总结：", explain_summary)
        append_list_section("优点：", explain_pros)
        append_list_section("需要注意：", explain_cons)
        append_text_section("建议：", explain_recommendation)

    next_actions = final_result.get("next_actions")
    append_list_section("下一步建议：", next_actions)

    followup_questions = final_result.get("followup_questions")
    append_list_section("你还可以继续确认：", followup_questions)

    missing_info_items = final_result.get("missing_info_items")
    append_list_section("当前还缺：", missing_info_items)

    # 2) 保留原始字段并放到后面
    append_text_section("原始总结：", summary)
    append_list_section("原始 reasons：", reasons)

    risk_lines: List[str] = []
    if isinstance(risks, list):
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
                risk_lines.append(risk_line)
            else:
                text = str(item).strip()
                if text:
                    risk_lines.append(f"- {text}")
    if risk_lines:
        if section_added:
            lines.append("")
        lines.append("原始 risks：")
        lines.extend(risk_lines)
        section_added = True

    append_text_section("原始 recommendation：", recommendation)

    cleaned_lines = _trim_trailing_blank_lines(lines)
    return "\n".join(cleaned_lines).strip()


def _trim_trailing_blank_lines(lines: List[str]) -> List[str]:
    result = list(lines)
    while result and result[-1] == "":
        result.pop()
    return result
