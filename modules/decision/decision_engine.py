from typing import Any, Dict, List


def build_decision_result(final_result: Dict[str, Any]) -> Dict[str, Any]:
    final_result = final_result or {}

    risks = final_result.get("risks") or []
    missing_info_items = final_result.get("missing_info_items") or []
    explain_result = final_result.get("explain_result") or {}
    next_actions = final_result.get("next_actions") or []

    high_risk_count = 0
    medium_risk_count = 0

    for item in risks:
        if isinstance(item, dict):
            level = str(
                item.get("level")
                or item.get("severity")
                or item.get("risk_level")
                or "medium"
            ).strip().lower()
        else:
            level = "medium"

        if level == "high":
            high_risk_count += 1
        elif level == "medium":
            medium_risk_count += 1

    missing_count = len(missing_info_items) if isinstance(missing_info_items, list) else 0

    explain_recommendation = ""
    if isinstance(explain_result, dict):
        explain_recommendation = str(explain_result.get("recommendation") or "").strip()

    if high_risk_count >= 2:
        status = "not_recommended"
        label = "当前不建议继续"
        reason = "因为高风险项较多，当前阶段直接继续的风险过高。"
    elif high_risk_count == 1:
        status = "review_required"
        label = "需要先处理高风险项"
        reason = "当前存在至少 1 个高风险项，建议先处理再继续。"
    elif missing_count >= 3:
        status = "info_needed"
        label = "需要先补充关键信息"
        reason = "当前缺失信息较多，直接下结论还不够稳。"
    elif medium_risk_count >= 3:
        status = "review_required"
        label = "建议继续核查后再决定"
        reason = "当前中风险项较多，建议继续核查关键细节。"
    else:
        status = "can_proceed"
        label = "可以继续推进"
        reason = "当前没有明显阻断项，整体可继续推进。"

    confidence = _build_confidence(
        high_risk_count=high_risk_count,
        medium_risk_count=medium_risk_count,
        missing_count=missing_count,
    )

    action_hint = _build_action_hint(
        status=status,
        explain_recommendation=explain_recommendation,
        next_actions=next_actions,
    )

    return {
        "status": status,
        "label": label,
        "reason": reason,
        "confidence": confidence,
        "action_hint": action_hint,
    }


def _build_confidence(high_risk_count: int, medium_risk_count: int, missing_count: int) -> str:
    if missing_count >= 4:
        return "low"

    if high_risk_count >= 1:
        return "medium"

    if medium_risk_count >= 3:
        return "medium"

    return "high"


def _build_action_hint(status: str, explain_recommendation: str, next_actions: List[Any]) -> str:
    if explain_recommendation:
        return explain_recommendation

    if isinstance(next_actions, list):
        for item in next_actions:
            text = str(item).strip()
            if text:
                return text

    if status == "not_recommended":
        return "建议先不要继续，先逐条解决高风险问题。"

    if status == "review_required":
        return "建议先核查关键风险，再决定是否继续。"

    if status == "info_needed":
        return "建议先补充缺失信息，再继续判断。"

    return "建议按当前结果继续推进。"
