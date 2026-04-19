from typing import Any, Dict, List


def build_next_actions(final_result: Dict[str, Any]) -> List[str]:
    final_result = final_result or {}

    explain_result = final_result.get("explain_result") or {}
    risks = final_result.get("risks") or []
    recommendation = str(final_result.get("recommendation") or "").strip()

    actions: List[str] = []

    if isinstance(explain_result, dict):
        explain_recommendation = str(explain_result.get("recommendation") or "").strip()
        if explain_recommendation:
            actions.append(f"先按当前建议处理：{explain_recommendation}")

        explain_cons = explain_result.get("cons") or []
        if isinstance(explain_cons, list):
            for item in explain_cons[:2]:
                text = str(item).strip()
                if text:
                    actions.append(f"优先核查：{text}")

    high_risks = []
    medium_risks = []

    for item in risks:
        if isinstance(item, dict):
            title = str(item.get("title") or item.get("name") or item.get("risk") or item.get("issue") or "Unknown risk").strip()
            level = str(item.get("level") or item.get("severity") or item.get("risk_level") or "medium").strip().lower()
        else:
            title = str(item).strip()
            level = "medium"

        if not title:
            continue

        if level == "high":
            high_risks.append(title)
        elif level == "medium":
            medium_risks.append(title)

    for title in high_risks[:2]:
        actions.append(f"立即处理高风险项：{title}")

    if not high_risks:
        for title in medium_risks[:2]:
            actions.append(f"继续补查中风险项：{title}")

    if recommendation:
        actions.append(f"结合原始 recommendation 再确认一次：{recommendation}")

    if not actions:
        actions.append("先补充更多信息，再继续下一步分析。")

    return _deduplicate_items(actions)[:5]


def _deduplicate_items(items: List[str]) -> List[str]:
    seen = set()
    result = []

    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)

    return result
