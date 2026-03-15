# 房源推荐解释引擎：根据评分生成用户可读的推荐说明
# Module7 Phase1-A1：Explain Engine 基础解释框架


def _empty_explanation():
    """返回标准解释结构的空模板。"""
    return {
        "summary": "",
        "recommended": None,
        "positive_reasons": [],
        "not_recommended_reasons": [],
        "neutral_notes": [],
        "next_actions": [],
    }


def explain_house(house):
    """房源推荐解释：根据评分生成统一解释结构。"""
    if house is None or not isinstance(house, dict):
        return _empty_explanation()

    explanation = _empty_explanation()

    # Price explanation 租金解释
    if "price_score" in house:
        if house["price_score"] >= 80:
            explanation["positive_reasons"].append("Rent price is very competitive.")
        elif house["price_score"] >= 60:
            explanation["neutral_notes"].append("Rent price is acceptable.")
        else:
            explanation["not_recommended_reasons"].append("Rent price is relatively high.")

    # Commute explanation 通勤解释
    if "commute_score" in house:
        if house["commute_score"] >= 80:
            explanation["positive_reasons"].append("Commute distance is very convenient.")
        elif house["commute_score"] >= 60:
            explanation["neutral_notes"].append("Commute distance is acceptable.")
        else:
            explanation["not_recommended_reasons"].append("Commute distance may be inconvenient.")

    # Area explanation 地区解释
    if "area_score" in house:
        if house["area_score"] >= 80:
            explanation["positive_reasons"].append("Area quality is very good.")
        elif house["area_score"] >= 60:
            explanation["neutral_notes"].append("Area quality is decent.")
        else:
            explanation["not_recommended_reasons"].append("Area quality may be weaker.")

    # 根据 positive / not_recommended 数量生成 summary
    pos_count = len(explanation["positive_reasons"])
    neg_count = len(explanation["not_recommended_reasons"])
    if pos_count > neg_count:
        explanation["summary"] = "This property shows several strong advantages based on the evaluation."
    elif neg_count > pos_count:
        explanation["summary"] = "This property has several potential drawbacks and may require careful consideration."
    else:
        explanation["summary"] = "This property has a mixed profile with both strengths and trade-offs."

    # 设置 recommended
    if pos_count > neg_count:
        explanation["recommended"] = True
    elif neg_count > pos_count:
        explanation["recommended"] = False
    else:
        explanation["recommended"] = None

    # 默认建议 next_actions
    explanation["next_actions"] = [
        "Consider arranging a viewing.",
        "Compare with other properties in the same area.",
        "Verify the exact rent and bills structure.",
    ]

    return explanation


def build_risk_explanation(risk_result):
    """合同风险解释：将 Module3 的风险结果转为统一解释结构。"""
    if risk_result is None or not isinstance(risk_result, dict):
        return _empty_explanation()

    exp = _empty_explanation()

    # 兼容不同字段名的整体风险等级
    risk_level = (
        (risk_result.get("overall_risk_level") or "")
        or (risk_result.get("severity") or "")
        or (risk_result.get("risk_level") or "")
    ).strip().lower()

    risk_flags = risk_result.get("risk_flags") or []
    scenario = (risk_result.get("scenario") or "").strip()
    law_topics = risk_result.get("law_topics") or []
    legal_references = risk_result.get("legal_references") or []
    recommended_actions = risk_result.get("recommended_actions") or []
    evidence_required = risk_result.get("evidence_required") or []
    possible_outcomes = risk_result.get("possible_outcomes") or []
    missing_clauses = risk_result.get("missing_clauses") or []
    weak_clauses = risk_result.get("weak_clauses") or []
    highlighted_clauses = risk_result.get("highlighted_clauses") or []
    risk_clauses = risk_result.get("risk_clauses") or []

    # not_recommended_reasons：根据 risk_flags 与条款问题生成
    flag_to_reason = {
        "deposit_risk": "Deposit terms may be unclear or risky.",
        "rent_increase_risk": "Rent increase clause may create risk.",
        "repair_risk": "Repair responsibility is not clearly defined.",
        "notice_risk": "Notice or termination rules may be unclear.",
        "eviction_risk": "Eviction or possession process may create significant risk.",
        "fee_charge_risk": "Fees or additional charges may be problematic.",
        "landlord_entry_risk": "Landlord access or entry rules may be unclear.",
    }
    seen_flags = set()
    for f in risk_flags:
        if not isinstance(f, str) or f in seen_flags:
            continue
        seen_flags.add(f)
        reason = flag_to_reason.get(f)
        if reason:
            exp["not_recommended_reasons"].append(reason)

    if missing_clauses:
        types = {m.get("clause_type") for m in missing_clauses if isinstance(m, dict)}
        if types:
            exp["not_recommended_reasons"].append(
                "Important clauses may be missing (e.g. %s)." % ", ".join(sorted(types))
            )

    if weak_clauses:
        types = {w.get("clause_type") for w in weak_clauses if isinstance(w, dict)}
        if types:
            exp["not_recommended_reasons"].append(
                "Some clauses exist but may be weak or unclear (e.g. %s)." % ", ".join(sorted(types))
            )

    if risk_clauses or highlighted_clauses:
        exp["not_recommended_reasons"].append(
            "Several contract clauses have been flagged as potentially risky and should be reviewed carefully."
        )

    # positive_reasons：对用户有利的因素
    if law_topics:
        exp["positive_reasons"].append("Relevant legal topics have been identified for this situation.")

    if legal_references:
        exp["positive_reasons"].append("Legal basis or references are available to support the analysis.")

    if recommended_actions:
        exp["positive_reasons"].append("Recommended actions are available to help manage the risks.")

    if evidence_required:
        exp["positive_reasons"].append("The system has suggested which evidence will be helpful to prepare.")

    if scenario:
        exp["positive_reasons"].append(
            "The dispute or contract has been classified into a scenario: %s." % scenario
        )

    if highlighted_clauses:
        exp["positive_reasons"].append("Key clauses have already been highlighted for focused review.")

    # neutral_notes：中性说明
    exp["neutral_notes"].append("Further document review may still be needed.")
    exp["neutral_notes"].append("Some conclusions may depend on the full signed contract and any side agreements.")
    exp["neutral_notes"].append("The risk level may change if new evidence appears or more information is provided.")

    # summary & recommended：优先使用整体风险等级
    pos_count = len(exp["positive_reasons"])
    neg_count = len(exp["not_recommended_reasons"])

    if risk_level == "high":
        exp["summary"] = (
            "This contract or dispute situation contains significant risks and should be reviewed carefully before proceeding."
        )
        exp["recommended"] = False
    elif risk_level == "medium":
        exp["summary"] = (
            "This situation has some contractual or legal concerns, but it may still be manageable with proper clarification and evidence."
        )
        exp["recommended"] = None
    elif risk_level in {"low", "none", ""}:
        exp["summary"] = (
            "No severe issue is immediately visible, but the key clauses and obligations should still be checked carefully."
        )
        # low/none 情况下，根据正负数量微调
        if neg_count > pos_count:
            exp["recommended"] = False
        elif pos_count > neg_count:
            exp["recommended"] = True
        else:
            exp["recommended"] = None
    else:
        # 无明确风险等级时，回退到正负数量判断
        if neg_count > pos_count:
            exp["summary"] = (
                "This contract or dispute situation has several potential drawbacks and may require careful consideration."
            )
            exp["recommended"] = False
        elif pos_count > neg_count:
            exp["summary"] = (
                "This situation shows several strengths in terms of legal structure or available actions."
            )
            exp["recommended"] = True
        else:
            exp["summary"] = (
                "This situation has a mixed profile with both strengths and trade-offs, and may require further review."
            )
            exp["recommended"] = None

    # next_actions：结合系统推荐动作与通用建议
    next_actions = []
    for act in recommended_actions:
        if isinstance(act, str):
            next_actions.append(act)
    # 通用建议
    next_actions.extend([
        "Save chats, emails, receipts, and payment records.",
        "Review deposit, repair, rent increase, and termination clauses carefully.",
        "Ask the landlord or agent to clarify unclear wording in writing.",
        "Prepare evidence before making a complaint or challenge.",
        "Request missing or unclear clauses to be clarified or added before signing.",
    ])
    # 去重保持顺序
    deduped = []
    seen = set()
    for a in next_actions:
        if not isinstance(a, str):
            continue
        if a not in seen:
            seen.add(a)
            deduped.append(a)
    exp["next_actions"] = deduped

    return exp


def build_explanation(data, explanation_type):
    """Explain Engine 统一入口：根据 explanation_type 分派到不同解释函数。"""
    if explanation_type == "house":
        return explain_house(data)
    if explanation_type == "risk":
        return build_risk_explanation(data)

    exp = _empty_explanation()
    exp["summary"] = "Unsupported explanation type."
    return exp


if __name__ == "__main__":
    # 房源解释示例
    sample_house = {
        "price_score": 85,
        "commute_score": 70,
        "area_score": 55,
    }
    house_result = explain_house(sample_house)
    print("House explanation:\n", house_result)

    # 合同风险解释示例（模拟 Module3 结果结构的精简版）
    sample_risk = {
        "overall_risk_level": "high",
        "risk_flags": ["deposit_risk", "repair_risk"],
        "scenario": "deposit_dispute",
        "law_topics": ["deposit_protection"],
        "legal_references": ["Housing Act 2004"],
        "recommended_actions": [
            "Check whether the deposit is protected in an approved scheme.",
            "Collect contracts, payment records, and chat logs.",
        ],
        "evidence_required": [
            "Tenancy agreement", "Deposit protection certificate", "Payment receipts",
        ],
        "possible_outcomes": [
            "The landlord explains the deduction grounds.",
            "Part or all of the deposit may be returned.",
        ],
        "missing_clauses": [
            {"clause_type": "termination_clause", "status": "missing"},
        ],
        "weak_clauses": [
            {"clause_type": "repair_clause", "status": "weak"},
        ],
    }
    risk_result = build_risk_explanation(sample_risk)
    print("\nRisk explanation:\n", risk_result)

    # 统一入口示例
    print("\nUnified explanation (risk):\n", build_explanation(sample_risk, "risk"))
