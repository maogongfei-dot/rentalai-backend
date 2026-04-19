from typing import Any, Dict, List


def build_followup_questions(final_result: Dict[str, Any]) -> List[str]:
    final_result = final_result or {}

    risks = final_result.get("risks") or []
    next_actions = final_result.get("next_actions") or []
    explain_result = final_result.get("explain_result") or {}
    summary = str(final_result.get("summary") or "").strip()

    questions: List[str] = []

    high_risk_titles: List[str] = []
    medium_risk_titles: List[str] = []

    for item in risks:
        if isinstance(item, dict):
            title = str(
                item.get("title")
                or item.get("name")
                or item.get("risk")
                or item.get("issue")
                or "Unknown risk"
            ).strip()
            level = str(
                item.get("level")
                or item.get("severity")
                or item.get("risk_level")
                or "medium"
            ).strip().lower()
        else:
            title = str(item).strip()
            level = "medium"

        if not title:
            continue

        if level == "high":
            high_risk_titles.append(title)
        elif level == "medium":
            medium_risk_titles.append(title)

    for title in high_risk_titles[:2]:
        questions.append(f"关于“{title}”，你现在是否已经有更具体的证据或补充信息？")

    if not high_risk_titles:
        for title in medium_risk_titles[:2]:
            questions.append(f"关于“{title}”，你是否想继续补充细节让我进一步判断？")

    if isinstance(explain_result, dict):
        recommendation = str(explain_result.get("recommendation") or "").strip()
        if recommendation:
            questions.append("你是否希望我根据当前建议，继续帮你拆成更具体的处理步骤？")

    if isinstance(next_actions, list) and next_actions:
        questions.append("你想先处理哪一条下一步建议？我可以按顺序带你继续。")

    if summary and not questions:
        questions.append("你是否希望我根据当前分析结果，继续追问几个关键问题来提高判断准确度？")

    if not questions:
        questions.append("你现在最想优先确认的是预算、风险、合同，还是下一步行动？")

    return _deduplicate_items(questions)[:5]


def _deduplicate_items(items: List[str]) -> List[str]:
    seen = set()
    result = []

    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)

    return result
