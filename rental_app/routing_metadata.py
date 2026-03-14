# Module3 Phase1-A5-7：统一路由元数据生成（routing metadata builder）
# 将 input_type / analysis_mode / response_focus / guided_summary / recommended_path / next_step_hint 的生成逻辑集中在此，便于主流程调用，为 A6 Action Engine 做准备。

from input_classifier import detect_input_type


def _get_analysis_mode_and_focus(input_type: str):
    """根据 input_type 返回 analysis_mode 与 response_focus。"""
    mapping = {
        "question": ("explain_only", "answer_user_question"),
        "contract_clause": ("clause_risk_review", "review_contract_risk"),
        "dispute": ("dispute_support", "suggest_next_steps"),
    }
    mode, focus = mapping.get(input_type, mapping["question"])
    return {"analysis_mode": mode, "response_focus": focus}


def _build_guided_summary(analysis_mode: str) -> str:
    """按 analysis_mode 生成引导性摘要。"""
    texts = {
        "explain_only": (
            "This appears to be mainly a user question. "
            "The system should focus on explaining the rule or contract meaning."
        ),
        "clause_risk_review": (
            "This appears to be a contract clause for review. "
            "The system should focus on identifying unfair, unclear, or risky terms."
        ),
        "dispute_support": (
            "This appears to be a dispute description. "
            "The system should focus on risk issues and practical next steps."
        ),
    }
    return texts.get(analysis_mode, texts["explain_only"])


def _get_recommended_path(analysis_mode: str) -> str:
    """根据 analysis_mode 返回下一步处理路径标签。"""
    mapping = {
        "explain_only": "explanation_path",
        "clause_risk_review": "contract_review_path",
        "dispute_support": "dispute_resolution_path",
    }
    return mapping.get(analysis_mode, "explanation_path")


def _get_next_step_hint(recommended_path: str) -> str:
    """根据 recommended_path 生成下一步提示。"""
    hints = {
        "explanation_path": "继续解释相关规则、合同含义或租房责任边界。",
        "contract_review_path": "继续审查合同条款，重点检查不公平、模糊或高风险内容。",
        "dispute_resolution_path": "继续整理纠纷事实、证据和可执行的下一步处理建议。",
    }
    return hints.get(recommended_path, hints["explanation_path"])


def get_path_recommended_actions(recommended_path: str) -> list:
    """
    Phase1-A6-1：根据 recommended_path 生成基础版推荐动作列表（action 标识）。
    供 Action Recommendation Engine 基础版使用。
    """
    actions = {
        "explanation_path": ["clarify_rule", "explain_contract_meaning"],
        "contract_review_path": ["review_clause_risk", "highlight_unfair_terms"],
        "dispute_resolution_path": ["collect_evidence", "prepare_next_steps", "suggest_formal_contact"],
    }
    return list(actions.get(recommended_path, actions["explanation_path"]))


# Phase1-A6-2：action code -> 中文可展示说明
ACTION_DETAILS_MAP = {
    "clarify_rule": "先明确相关规则、责任边界或租房场景中的适用条件。",
    "explain_contract_meaning": "解释合同条款的实际含义，以及它对租客或房东的影响。",
    "review_clause_risk": "审查该条款是否存在不公平、模糊或偏向单方的风险。",
    "highlight_unfair_terms": "标出可能不合理或需要重点关注的合同内容。",
    "collect_evidence": "整理聊天记录、合同、付款记录、照片等证据材料。",
    "prepare_next_steps": "先明确争议点，再整理下一步处理顺序。",
    "suggest_formal_contact": "如有需要，可准备正式沟通内容，例如邮件、书面通知或投诉。",
}

# Phase1-A6-3：action code -> 执行优先级（数字越小越优先）
ACTION_PRIORITY_MAP = {
    "collect_evidence": 1,
    "prepare_next_steps": 2,
    "suggest_formal_contact": 3,
    "clarify_rule": 1,
    "explain_contract_meaning": 2,
    "review_clause_risk": 1,
    "highlight_unfair_terms": 2,
}


def get_action_priority(action_code: str) -> int:
    """Phase1-A6-3：返回 action 的优先级数字，未知 code 返回 99。"""
    return ACTION_PRIORITY_MAP.get(action_code, 99)


def build_action_priority_map(recommended_actions: list) -> dict:
    """Phase1-A6-3：根据 recommended_actions 生成 action_priority_map。"""
    return {code: get_action_priority(code) for code in (recommended_actions or []) if isinstance(code, str)}


def build_ordered_action_details(recommended_actions: list) -> list:
    """Phase1-A6-3：按 priority 升序排列，输出适合前端展示的中文说明列表。"""
    if not recommended_actions:
        return []
    # 按优先级排序，同优先级保持原顺序
    sorted_codes = sorted(recommended_actions, key=lambda c: get_action_priority(c) if isinstance(c, str) else 99)
    out = []
    for code in sorted_codes:
        s = ACTION_DETAILS_MAP.get(code) if isinstance(code, str) else None
        if s:
            out.append(s)
    return out


def build_action_details(recommended_actions: list) -> list:
    """
    Phase1-A6-2：根据 recommended_actions 生成中文可展示的 action_details 列表。
    """
    out = []
    for code in recommended_actions or []:
        s = ACTION_DETAILS_MAP.get(code) if isinstance(code, str) else None
        if s:
            out.append(s)
    return out


def build_routing_metadata(text: str) -> dict:
    """
    统一生成与输入分流相关的路由元数据，供 Module3 主流程及后续 A6 使用。
    入参为原始输入文本；空文本时按 question 处理。
    返回包含 input_type / analysis_mode / response_focus / guided_summary / recommended_path / next_step_hint 的 dict。
    """
    raw = (text or "").strip()
    input_type = detect_input_type(raw) if raw else "question"
    mode_focus = _get_analysis_mode_and_focus(input_type)
    analysis_mode = mode_focus["analysis_mode"]
    response_focus = mode_focus["response_focus"]
    guided_summary = _build_guided_summary(analysis_mode)
    recommended_path = _get_recommended_path(analysis_mode)
    next_step_hint = _get_next_step_hint(recommended_path)
    # Phase1-A6-1: 根据 recommended_path 生成 recommended_actions（基础版 action 标识）
    recommended_actions = get_path_recommended_actions(recommended_path)
    # Phase1-A6-2: 根据 recommended_actions 生成中文可展示的 action_details
    action_details = build_action_details(recommended_actions)
    # Phase1-A6-3: 优先级映射与按优先级排序的可展示列表
    action_priority_map = build_action_priority_map(recommended_actions)
    ordered_action_details = build_ordered_action_details(recommended_actions)
    return {
        "input_type": input_type,
        "analysis_mode": analysis_mode,
        "response_focus": response_focus,
        "guided_summary": guided_summary,
        "recommended_path": recommended_path,
        "next_step_hint": next_step_hint,
        "recommended_actions": recommended_actions,
        "action_details": action_details,
        "action_priority_map": action_priority_map,
        "ordered_action_details": ordered_action_details,
    }
