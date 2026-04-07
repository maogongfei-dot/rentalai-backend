from __future__ import annotations

from typing import Any, Dict, List


def _safe_get_list(data: Dict[str, Any], *keys: str) -> List[str]:
    for key in keys:
        value = data.get(key)
        if isinstance(value, list):
            result = []
            for item in value:
                if item is None:
                    continue
                text = str(item).strip()
                if text:
                    result.append(text)
            if result:
                return result
    return []


def _safe_get_dict(data: Dict[str, Any], *keys: str) -> Dict[str, Any]:
    for key in keys:
        value = data.get(key)
        if isinstance(value, dict):
            return value
    return {}


def _safe_get_str(data: Dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = data.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return ""


def _dedupe_keep_order(items: List[str], limit: int | None = None) -> List[str]:
    seen = set()
    result = []
    for item in items:
        text = str(item).strip()
        if not text:
            continue
        if text in seen:
            continue
        seen.add(text)
        result.append(text)
        if limit is not None and len(result) >= limit:
            break
    return result


def _flatten_action_sources(system_result: Dict[str, Any]) -> List[str]:
    actions: List[str] = []

    actions.extend(_safe_get_list(system_result, "priority_actions"))
    actions.extend(_safe_get_list(system_result, "human_next_steps"))
    actions.extend(_safe_get_list(system_result, "next_steps"))
    actions.extend(_safe_get_list(system_result, "recommended_actions"))
    actions.extend(_safe_get_list(system_result, "actions"))
    actions.extend(_safe_get_list(system_result, "action_plan"))

    timeline = _safe_get_dict(system_result, "action_timeline")
    actions.extend(_safe_get_list(timeline, "immediate"))
    actions.extend(_safe_get_list(timeline, "today"))
    actions.extend(_safe_get_list(timeline, "later"))

    return _dedupe_keep_order(actions)


def _contains_any(text: str, keywords: List[str]) -> bool:
    lower_text = text.lower()
    return any(keyword.lower() in lower_text for keyword in keywords)


def _is_immediate_action(text: str) -> bool:
    keywords = [
        "先",
        "立即",
        "马上",
        "尽快",
        "保存",
        "保留",
        "聊天记录",
        "付款记录",
        "付款凭证",
        "证据",
        "截图",
        "标出",
        "条款",
        "暂停",
        "不要签",
        "不要付款",
        "书面沟通",
        "发消息",
        "发给房东",
        "发给中介",
    ]
    return _contains_any(text, keywords)


def _is_later_action(text: str) -> bool:
    keywords = [
        "后续",
        "再决定",
        "根据对方回复",
        "投诉",
        "tribunal",
        "ombudsman",
        "council",
        "legal help",
        "法律帮助",
        "升级处理",
        "正式处理",
        "继续跟进",
        "进一步处理",
        "报告",
        "report",
    ]
    return _contains_any(text, keywords)


def _default_immediate_action(system_result: Dict[str, Any]) -> List[str]:
    urgency_level = _safe_get_str(system_result, "urgency_level")
    recommended_decision = _safe_get_str(system_result, "recommended_decision")

    if urgency_level == "high":
        return ["先保存好现有合同、聊天记录和付款凭证。"]

    if recommended_decision in {"pause", "escalate"}:
        return ["先把关键条款、聊天记录和付款凭证整理出来。"]

    return ["先整理现有材料和问题点。"]


def _default_today_action(system_result: Dict[str, Any]) -> List[str]:
    recommended_decision = _safe_get_str(system_result, "recommended_decision")

    if recommended_decision == "pause":
        return ["今天内先确认关键条款和仍缺的信息。"]

    if recommended_decision == "escalate":
        return ["今天内先完成书面说明并整理证据。"]

    return ["今天内把问题说明和关键材料整理清楚。"]


def _default_later_action(system_result: Dict[str, Any]) -> List[str]:
    recommended_decision = _safe_get_str(system_result, "recommended_decision")

    if recommended_decision == "escalate":
        return ["后续再根据对方回复决定是否进入正式处理路径。"]

    return ["后续再根据确认结果决定是否继续推进。"]


def build_action_timeline(system_result: Dict[str, Any]) -> Dict[str, List[str]]:
    actions = _flatten_action_sources(system_result)
    urgency_level = _safe_get_str(system_result, "urgency_level")
    recommended_decision = _safe_get_str(system_result, "recommended_decision")

    immediate: List[str] = []
    today: List[str] = []
    later: List[str] = []

    for action in actions:
        if len(immediate) < 2 and _is_immediate_action(action):
            immediate.append(action)
            continue

        if len(later) < 3 and _is_later_action(action):
            later.append(action)
            continue

        if len(today) < 3:
            today.append(action)

    immediate = _dedupe_keep_order(immediate, limit=2)
    today = _dedupe_keep_order(today, limit=3)
    later = _dedupe_keep_order(later, limit=3)

    if not immediate:
        immediate = _default_immediate_action(system_result)

    if not today:
        today = _default_today_action(system_result)

    if not later and recommended_decision in {"pause", "escalate"}:
        later = _default_later_action(system_result)

    if recommended_decision == "proceed":
        later = later[:1]

    if urgency_level == "high" and today and len(immediate) < 2:
        first_today = today.pop(0)
        if first_today not in immediate:
            immediate.append(first_today)
        immediate = _dedupe_keep_order(immediate, limit=2)

    return {
        "immediate": _dedupe_keep_order(immediate, limit=2),
        "today": _dedupe_keep_order(today, limit=3),
        "later": _dedupe_keep_order(later, limit=3),
    }


def build_timeline_reason(system_result: Dict[str, Any]) -> str:
    urgency_level = _safe_get_str(system_result, "urgency_level")
    recommended_decision = _safe_get_str(system_result, "recommended_decision")
    missing_information = _safe_get_list(system_result, "missing_information")

    if recommended_decision == "escalate":
        return "因为当前已经不只是普通确认问题，所以建议先做关键留证和书面沟通，再决定是否进入正式处理。"

    if recommended_decision == "pause":
        return "因为目前还有关键信息和条款需要先确认，所以建议先整理和确认，再决定后续动作。"

    if urgency_level == "high":
        return "因为这件事不适合继续拖延，所以建议先做最关键的留证和沟通动作，其他步骤放在后面。"

    if missing_information:
        return "因为当前还缺少部分关键信息，所以建议先补信息和整理材料，再继续往后处理。"

    return "因为当前已有初步处理方向，所以建议按先整理、再确认、后续推进的顺序来处理。"


def build_human_timeline_notice(system_result: Dict[str, Any]) -> str:
    urgency_level = _safe_get_str(system_result, "urgency_level")
    recommended_decision = _safe_get_str(system_result, "recommended_decision")

    if recommended_decision == "escalate":
        return "先把最关键的留证和书面动作做起来，后面的正式处理再按情况推进。"

    if recommended_decision == "pause":
        return "现在更适合先确认和补材料，不需要一次把所有动作都做完。"

    if urgency_level == "high":
        return "这类情况最好先把最重要的动作做掉，越往后拖越容易被动。"

    return "现在不需要一次处理完全部事情，先按顺序做最稳。"