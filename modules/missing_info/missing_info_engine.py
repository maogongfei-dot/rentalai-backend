from typing import Any, Dict, List


def build_missing_info_items(final_result: Dict[str, Any]) -> List[str]:
    final_result = final_result or {}

    summary = str(final_result.get("summary") or "").strip()
    risks = final_result.get("risks") or []
    reasons = final_result.get("reasons") or []
    explain_result = final_result.get("explain_result") or {}
    next_actions = final_result.get("next_actions") or []
    followup_questions = final_result.get("followup_questions") or []

    missing_items: List[str] = []

    if not summary:
        missing_items.append("缺少整体总结信息")

    if not risks:
        missing_items.append("缺少风险明细")

    if not reasons:
        missing_items.append("缺少有利因素或原因说明")

    if not isinstance(explain_result, dict) or not explain_result:
        missing_items.append("缺少 explain_result 解释层结果")
    else:
        if not str(explain_result.get("summary") or "").strip():
            missing_items.append("缺少 explain summary")
        if not str(explain_result.get("recommendation") or "").strip():
            missing_items.append("缺少 explain recommendation")

    if not isinstance(next_actions, list) or not next_actions:
        missing_items.append("缺少下一步行动建议")

    if not isinstance(followup_questions, list) or not followup_questions:
        missing_items.append("缺少后续追问问题")

    high_risk_exists = False
    for item in risks:
        if isinstance(item, dict):
            level = str(
                item.get("level")
                or item.get("severity")
                or item.get("risk_level")
                or "medium"
            ).strip().lower()
            if level == "high":
                high_risk_exists = True
                break

    if high_risk_exists and (not isinstance(next_actions, list) or not next_actions):
        missing_items.append("存在高风险项，但缺少对应处理动作")

    return _deduplicate_items(missing_items)


def _deduplicate_items(items: List[str]) -> List[str]:
    seen = set()
    result = []

    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)

    return result
