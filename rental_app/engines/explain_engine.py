# 房源推荐解释引擎：根据评分生成用户可读的推荐说明
# Module7 Phase1-A1：Explain Engine 基础解释框架
# Phase1-A4：字段兼容 + 文案细化
# Phase2-A1：原因排序与重点提炼


def _empty_explanation():
    """返回标准解释结构的空模板。Phase2-A1: 扩展 top_positive_reasons, top_risk_reasons, decision_focus。"""
    return {
        "summary": "",
        "recommended": None,
        "positive_reasons": [],
        "not_recommended_reasons": [],
        "neutral_notes": [],
        "next_actions": [],
        "top_positive_reasons": [],
        "top_risk_reasons": [],
        "decision_focus": "",
    }


# ---------- Phase1-A4: 轻量辅助函数 ----------

def _get_first_value(data, keys, default=None):
    """从 dict 中按 keys 顺序取第一个存在的非空值。"""
    if not data or not isinstance(data, dict):
        return default
    for k in keys:
        v = data.get(k)
        if v is not None and v != "":
            return v
    # 兼容嵌套 scores
    scores = data.get("scores")
    if isinstance(scores, dict):
        for k in keys:
            v = scores.get(k)
            if v is not None and v != "":
                return v
    return default


def _safe_list(value):
    """将任意值转为 list，None/非序列 -> []。"""
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, (tuple, set)):
        return list(value)
    if isinstance(value, (str, dict)):
        return [value]
    return []


def _normalize_text(text):
    """清洗文本：strip + lower，空 -> ''。"""
    if text is None:
        return ""
    return str(text).strip().lower()


def _add_unique(items, value, seen=None):
    """向 items 追加 value，去重。seen 为 set，可外部传入以跨多次调用去重。"""
    if not isinstance(value, str) or not value.strip():
        return
    s = seen if seen is not None else set()
    if value in s:
        return
    s.add(value)
    items.append(value)


def _score_band(score, scale_100=True):
    """将分数转为档位：'high'(>=80), 'mid'(60-79), 'low'(<60)。score 为 None 返回 None。"""
    if score is None:
        return None
    try:
        v = float(score)
    except (TypeError, ValueError):
        return None
    if v <= 10 and v >= 0 and not scale_100:
        v = v * 10
    if v >= 80:
        return "high"
    if v >= 60:
        return "mid"
    return "low"


def _to_float(value, default=None):
    """安全转 float。"""
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


# ---------- Phase2-A1: 原因排序与重点提炼 ----------

# House: 负面高优先级关键词（匹配则优先）
_HOUSE_NEG_PRIORITY = [
    ("price", "high", "rent"),
    ("commute", "poor", "long", "inconvenient"),
    ("area", "weaker", "mismatch"),
    ("distance", "far"),
    ("bills", "unclear", "unfavorable"),
]

# House: 正面高优先级关键词
_HOUSE_POS_PRIORITY = [
    ("strong", "overall", "balance"),
    ("competitive", "rent", "price"),
    ("convenient", "commute"),
    ("area", "good", "quality"),
    ("bills", "included", "favourable"),
    ("distance", "target", "good"),
]

# Risk: 负面高优先级关键词
_RISK_NEG_PRIORITY = [
    ("missing", "clauses"),
    ("weak", "unclear", "vague"),
    ("deposit", "unclear", "risky"),
    ("repair", "responsibility", "defined"),
    ("termination", "clause", "notice"),
    ("rent increase", "rent_increase"),
    ("evidence", "insufficient"),
    ("legal", "significant", "risky"),
    ("flagged", "potentially risky"),
]

# Risk: 正面高优先级关键词
_RISK_POS_PRIORITY = [
    ("legal", "basis", "references"),
    ("actions", "available"),
    ("evidence", "helpful", "prepare"),
    ("scenario", "classified"),
    ("clauses", "highlighted"),
]


def _rank_reason(reason: str, context: str = "", reason_type: str = "house") -> int:
    """规则优先级打分：匹配高优先级关键词则得分高，用于排序。返回 0-100，越高越优先。"""
    if not reason or not isinstance(reason, str):
        return 0
    r = _normalize_text(reason)
    if not r:
        return 0
    priority_list = []
    if context == "neg" and reason_type == "risk":
        priority_list = _RISK_NEG_PRIORITY
    elif context == "pos" and reason_type == "risk":
        priority_list = _RISK_POS_PRIORITY
    elif context == "neg" and reason_type == "house":
        priority_list = _HOUSE_NEG_PRIORITY
    elif context == "pos" and reason_type == "house":
        priority_list = _HOUSE_POS_PRIORITY
    for i, keywords in enumerate(priority_list):
        match_count = sum(1 for kw in keywords if kw in r)
        if match_count >= 1:
            return max(10, 100 - i * 10)
    return 50


def _select_top_reasons(reasons: list, top_n: int = 3, context: str = "pos", reason_type: str = "house") -> list:
    """从 reasons 中按优先级选出 top_n 条，去重保留顺序。"""
    if not reasons:
        return []
    seen = set()
    scored = []
    for r in reasons:
        if not isinstance(r, str) or not r.strip():
            continue
        if r in seen:
            continue
        seen.add(r)
        score = _rank_reason(r, context, reason_type)
        scored.append((score, r))
    scored.sort(key=lambda x: (-x[0], x[1]))
    return [r for _, r in scored[:top_n]]


def _build_decision_focus(explanation: dict, explanation_type: str) -> str:
    """根据 explanation 生成一句话 decision_focus。"""
    if not explanation or not isinstance(explanation, dict):
        return "Consider the key factors before making a decision."
    top_neg = explanation.get("top_risk_reasons") or []
    top_pos = explanation.get("top_positive_reasons") or []
    neg = explanation.get("not_recommended_reasons") or []
    pos = explanation.get("positive_reasons") or []
    rec = explanation.get("recommended")

    if explanation_type == "house":
        if top_neg and (rec is False or len(neg) > len(pos)):
            return "The main decision issue is whether the weaker price, commute, or area fit is acceptable for your needs."
        if top_pos and (rec is True or len(pos) > len(neg)):
            return "The main decision focus is whether you want to move quickly on a property that already performs well across key factors."
        return "The key decision is whether the strengths of this property outweigh its trade-offs."

    if explanation_type == "risk":
        if rec is False or (top_neg and len(neg) >= 2):
            return "The key issue is to clarify the major contractual risks before you proceed any further."
        if rec is None and (top_neg or top_pos):
            return "The main focus should be on verifying the uncertain clauses and preparing supporting evidence."
        return "The key focus is to confirm the remaining details before treating the situation as safe."


def explain_house(house):
    """房源推荐解释：根据评分生成统一解释结构。Phase1-A4: 字段兼容 + 文案细化。"""
    if house is None or not isinstance(house, dict):
        return _empty_explanation()

    exp = _empty_explanation()
    weak_scores = []  # 记录低分维度，用于动态 next_actions

    def _get_score(*keys):
        v = _get_first_value(house, list(keys))
        if v is None:
            return None
        f = _to_float(v)
        if f is not None and 0 <= f <= 10 and f != 100:
            f = f * 10  # 0-10 -> 0-100
        return f

    # Price
    price_score = _get_score("price_score")
    if price_score is not None:
        band = _score_band(price_score, scale_100=True)
        if band == "high":
            exp["positive_reasons"].append("Rent price is very competitive.")
        elif band == "mid":
            exp["neutral_notes"].append("Rent price is acceptable.")
        else:
            exp["not_recommended_reasons"].append("Rent price is relatively high.")
            weak_scores.append("price_score")

    # Commute
    commute_score = _get_score("commute_score")
    if commute_score is not None:
        band = _score_band(commute_score, scale_100=True)
        if band == "high":
            exp["positive_reasons"].append("Commute distance is very convenient.")
        elif band == "mid":
            exp["neutral_notes"].append("Commute distance is acceptable.")
        else:
            exp["not_recommended_reasons"].append("Commute distance may be inconvenient.")
            weak_scores.append("commute_score")

    # Area
    area_score = _get_score("area_score")
    if area_score is not None:
        band = _score_band(area_score, scale_100=True)
        if band == "high":
            exp["positive_reasons"].append("Area quality is very good.")
        elif band == "mid":
            exp["neutral_notes"].append("Area quality is decent.")
        else:
            exp["not_recommended_reasons"].append("Area quality may be weaker.")
            weak_scores.append("area_score")

    # Bills
    bills_score = _get_score("bills_score")
    if bills_score is not None:
        band = _score_band(bills_score, scale_100=True)
        if band == "high":
            exp["positive_reasons"].append("Bills inclusion is favourable.")
        elif band == "low":
            weak_scores.append("bills_score")

    # Bedrooms / distance (可选)
    bedrooms_score = _get_score("bedrooms_score")
    if bedrooms_score is not None and _score_band(bedrooms_score) == "low":
        weak_scores.append("bedrooms_score")
    distance_score = _get_score("distance_score")
    if distance_score is not None and _score_band(distance_score) == "low":
        weak_scores.append("distance_score")

    # Summary：结合 final_score 与正负数量
    pos_count = len(exp["positive_reasons"])
    neg_count = len(exp["not_recommended_reasons"])
    final_score = _get_first_value(house, ["final_score", "score", "total_score"])
    final_f = _to_float(final_score)

    if pos_count == 0 and neg_count == 0 and final_f is None:
        exp["summary"] = "Insufficient data for a detailed evaluation; consider adding more property details."
    elif pos_count > neg_count and (final_f is None or final_f >= 70):
        exp["summary"] = (
            "This property appears to be a strong overall option, with good balance across price, commute, and area-related factors."
        )
    elif neg_count > pos_count or (final_f is not None and final_f < 50):
        exp["summary"] = (
            "This property seems less attractive overall and may require extra caution unless there are strong personal reasons to keep it under consideration."
        )
    else:
        exp["summary"] = (
            "This property has a mixed profile. It offers some advantages, but there are also trade-offs that should be checked before making a decision."
        )

    # recommended
    if pos_count > neg_count:
        exp["recommended"] = True
    elif neg_count > pos_count:
        exp["recommended"] = False
    else:
        exp["recommended"] = None

    # next_actions：动态根据弱项生成
    actions = []
    seen = set()
    _add_unique(actions, "Consider arranging a viewing.", seen)
    _add_unique(actions, "Compare with other properties in the same area.", seen)
    if "price_score" in weak_scores:
        _add_unique(actions, "Compare this rent with similar listings nearby.", seen)
    if "commute_score" in weak_scores:
        _add_unique(actions, "Check the real commute route and travel time during peak hours.", seen)
    if "bills_score" in weak_scores:
        _add_unique(actions, "Confirm exactly which bills are included.", seen)
    if "area_score" in weak_scores:
        _add_unique(actions, "Review the area fit based on your personal priorities.", seen)
    if "distance_score" in weak_scores:
        _add_unique(actions, "Check whether the location is too far from your target area.", seen)
    _add_unique(actions, "Verify the exact rent and bills structure.", seen)
    exp["next_actions"] = actions[:6]

    # Phase2-A1: 提炼 top_positive_reasons / top_risk_reasons / decision_focus
    pos_reasons = exp.get("positive_reasons") or []
    neg_reasons = exp.get("not_recommended_reasons") or []
    exp["top_positive_reasons"] = _select_top_reasons(pos_reasons, top_n=3, context="pos", reason_type="house")
    if not exp["top_positive_reasons"] and pos_reasons:
        exp["top_positive_reasons"] = pos_reasons[:3]
    exp["top_risk_reasons"] = _select_top_reasons(neg_reasons, top_n=3, context="neg", reason_type="house")
    if not exp["top_risk_reasons"] and neg_reasons:
        exp["top_risk_reasons"] = neg_reasons[:3]
    exp["decision_focus"] = _build_decision_focus(exp, "house")

    return exp


def build_risk_explanation(risk_result):
    """合同风险解释：将 Module3 的风险结果转为统一解释结构。Phase1-A4: 字段兼容 + 文案细化。"""
    if risk_result is None or not isinstance(risk_result, dict):
        return _empty_explanation()

    exp = _empty_explanation()

    # 字段兼容：risk_level
    risk_level = _normalize_text(
        _get_first_value(risk_result, ["overall_risk_level", "severity", "risk_level", "overall_risk"])
    )

    # 从 risk_score / structured_risk_score 推导 risk_level
    if not risk_level:
        score = _get_first_value(risk_result, ["risk_score", "structured_risk_score"])
        v = _to_float(score)
        if v is not None:
            if v >= 7:
                risk_level = "high"
            elif v >= 4:
                risk_level = "medium"
            else:
                risk_level = "low"

    # 字段兼容：issues / risk_flags / detected_risks / highlighted_risks / matched_categories
    risk_flags = _safe_list(risk_result.get("risk_flags"))
    if not risk_flags:
        risk_flags = _safe_list(risk_result.get("matched_categories"))
    if not risk_flags:
        for k in ["issues", "detected_risks", "highlighted_risks"]:
            risk_flags.extend(_safe_list(risk_result.get(k)))

    # 字段兼容：actions / recommended_actions / action_steps
    recommended_actions = _safe_list(risk_result.get("recommended_actions"))
    if not recommended_actions:
        recommended_actions = _safe_list(risk_result.get("actions")) or _safe_list(risk_result.get("action_steps"))

    # 字段兼容：legal_basis / legal_references / legal_explanations
    legal_refs = _safe_list(risk_result.get("legal_references"))
    if not legal_refs:
        legal_refs = _safe_list(risk_result.get("legal_basis")) or _safe_list(risk_result.get("legal_explanations"))

    # 字段兼容：evidence_needed / evidence_required / evidence_list
    evidence_list = _safe_list(risk_result.get("evidence_required"))
    if not evidence_list:
        evidence_list = _safe_list(risk_result.get("evidence_needed")) or _safe_list(risk_result.get("evidence_list"))

    simple_risk_reasons = _safe_list(risk_result.get("risk_reasons"))
    scenario = _normalize_text(risk_result.get("scenario"))
    law_topics = _safe_list(risk_result.get("law_topics"))
    possible_outcomes = _safe_list(risk_result.get("possible_outcomes")) or _safe_list(risk_result.get("outcomes"))
    missing_clauses = _safe_list(risk_result.get("missing_clauses"))
    weak_clauses = _safe_list(risk_result.get("weak_clauses"))
    highlighted_clauses = _safe_list(risk_result.get("highlighted_clauses"))
    risk_clauses = _safe_list(risk_result.get("risk_clauses"))
    matched_rules = _safe_list(risk_result.get("matched_rules"))

    # not_recommended_reasons
    flag_to_reason = {
        "deposit_risk": "Deposit terms may be unclear or risky.",
        "rent_increase_risk": "Rent increase clause may create risk.",
        "repair_risk": "Repair responsibility is not clearly defined.",
        "notice_risk": "Notice or termination rules may be unclear.",
        "eviction_risk": "Eviction or possession process may create significant risk.",
        "fee_charge_risk": "Fees or additional charges may be problematic.",
        "landlord_entry_risk": "Landlord access or entry rules may be unclear.",
        "scam_risk": "Suspicious payment or scam-related signals detected.",
        "contract_risk": "Contract or written agreement may be missing or unclear.",
        "pressure_risk": "Pressure or urgency tactics may be present.",
    }
    seen_reasons = set()
    for f in risk_flags:
        if not isinstance(f, str) or f in seen_reasons:
            continue
        seen_reasons.add(f)
        reason = flag_to_reason.get(f)
        if reason:
            _add_unique(exp["not_recommended_reasons"], reason, seen_reasons)

    for r in simple_risk_reasons:
        if isinstance(r, str) and r.strip():
            _add_unique(exp["not_recommended_reasons"], r, seen_reasons)

    if matched_rules and not simple_risk_reasons:
        _add_unique(
            exp["not_recommended_reasons"],
            "Matched risk rules: %s." % ", ".join(matched_rules[:5]),
            seen_reasons
        )

    if missing_clauses:
        types = set()
        for m in missing_clauses:
            if isinstance(m, dict):
                t = m.get("clause_type") or m.get("type")
                if t:
                    types.add(str(t))
            elif isinstance(m, str):
                types.add(m)
        if types:
            _add_unique(
                exp["not_recommended_reasons"],
                "Important clauses may be missing (e.g. %s)." % ", ".join(sorted(types)[:5]),
                seen_reasons
            )

    if weak_clauses:
        types = set()
        for w in weak_clauses:
            if isinstance(w, dict):
                t = w.get("clause_type") or w.get("type")
                if t:
                    types.add(str(t))
            elif isinstance(w, str):
                types.add(w)
        if types:
            _add_unique(
                exp["not_recommended_reasons"],
                "Some clauses exist but may be weak or unclear (e.g. %s)." % ", ".join(sorted(types)[:5]),
                seen_reasons
            )

    if risk_clauses or highlighted_clauses:
        _add_unique(
            exp["not_recommended_reasons"],
            "Several contract clauses have been flagged as potentially risky and should be reviewed carefully.",
            seen_reasons
        )

    # positive_reasons
    if law_topics:
        _add_unique(exp["positive_reasons"], "Relevant legal topics have been identified for this situation.")
    if legal_refs:
        _add_unique(exp["positive_reasons"], "Legal basis or references are available to support the analysis.")
    if recommended_actions:
        _add_unique(exp["positive_reasons"], "Recommended actions are available to help manage the risks.")
    if evidence_list:
        _add_unique(exp["positive_reasons"], "The system has suggested which evidence will be helpful to prepare.")
    if scenario:
        _add_unique(exp["positive_reasons"], "The dispute or contract has been classified into a scenario: %s." % scenario)
    if highlighted_clauses:
        _add_unique(exp["positive_reasons"], "Key clauses have already been highlighted for focused review.")

    # neutral_notes
    _add_unique(exp["neutral_notes"], "Further document review may still be needed.")
    _add_unique(exp["neutral_notes"], "Some conclusions may depend on the full signed contract and any side agreements.")
    _add_unique(exp["neutral_notes"], "The risk level may change if new evidence appears or more information is provided.")

    # summary：细化文案
    pos_count = len(exp["positive_reasons"])
    neg_count = len(exp["not_recommended_reasons"])
    issues_count = neg_count

    if risk_level == "high":
        exp["summary"] = (
            "This contract or dispute situation presents several meaningful risks, so it would be safer to clarify the key issues before moving forward."
        )
        exp["recommended"] = False
    elif risk_level == "medium":
        exp["summary"] = (
            "This situation is not necessarily unmanageable, but there are enough concerns to justify a careful review of the contract terms and supporting evidence."
        )
        exp["recommended"] = None
    elif risk_level in {"low", "none", ""}:
        exp["summary"] = (
            "No major red flag is immediately obvious from the current result, but the main clauses and responsibilities should still be verified."
        )
        if neg_count > pos_count:
            exp["recommended"] = False
        elif pos_count > neg_count:
            exp["recommended"] = True
        else:
            exp["recommended"] = None
    else:
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

    # next_actions：动态根据字段生成
    actions = []
    seen = set()
    for act in recommended_actions:
        if isinstance(act, str) and act.strip():
            _add_unique(actions, act, seen)
    if missing_clauses:
        _add_unique(actions, "Request the missing clauses to be added or clarified in writing.", seen)
    if weak_clauses:
        _add_unique(actions, "Ask for clearer wording on weak or vague clauses.", seen)
    if risk_flags or issues_count > 0:
        _add_unique(actions, "Review the identified risk points one by one before proceeding.", seen)
    if evidence_list:
        _add_unique(actions, "Prepare and organize supporting evidence before challenging the issue.", seen)
    if legal_refs:
        _add_unique(actions, "Use the identified legal basis to support your communication or complaint.", seen)
    _add_unique(actions, "Save chats, emails, receipts, and payment records.", seen)
    _add_unique(actions, "Review deposit, repair, rent increase, and termination clauses carefully.", seen)
    _add_unique(actions, "Ask the landlord or agent to clarify unclear wording in writing.", seen)
    _add_unique(actions, "Prepare evidence before making a complaint or challenge.", seen)
    exp["next_actions"] = actions[:6]

    # Phase2-A1: 提炼 top_positive_reasons / top_risk_reasons / decision_focus
    pos_reasons = exp.get("positive_reasons") or []
    neg_reasons = exp.get("not_recommended_reasons") or []
    exp["top_risk_reasons"] = _select_top_reasons(neg_reasons, top_n=3, context="neg", reason_type="risk")
    if not exp["top_risk_reasons"] and neg_reasons:
        exp["top_risk_reasons"] = neg_reasons[:3]
    exp["top_positive_reasons"] = _select_top_reasons(pos_reasons, top_n=3, context="pos", reason_type="risk")
    if not exp["top_positive_reasons"] and pos_reasons:
        exp["top_positive_reasons"] = pos_reasons[:3]
    exp["decision_focus"] = _build_decision_focus(exp, "risk")

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


def format_explanation_for_cli(explanation: dict, max_items: int = 3) -> str:
    """轻量 CLI 展示：将 explanation dict 转为简洁可读文本。Phase2-A1: 优先 summary, decision_focus, top_reasons。"""
    if not explanation or not isinstance(explanation, dict):
        return ""
    lines = []
    summary = (explanation.get("summary") or "").strip()
    if summary:
        lines.append("  Summary: %s" % summary)
    focus = (explanation.get("decision_focus") or "").strip()
    if focus:
        lines.append("  Decision focus: %s" % focus)
    rec = explanation.get("recommended")
    if rec is True:
        lines.append("  Recommended: Yes")
    elif rec is False:
        lines.append("  Recommended: No")
    elif rec is None and summary:
        lines.append("  Recommended: Mixed")
    # Phase2-A1: 优先展示 top_positive_reasons / top_risk_reasons
    top_pos = (explanation.get("top_positive_reasons") or [])[:max_items]
    if top_pos:
        lines.append("  Top positives: %s" % "; ".join(top_pos))
    else:
        pos = (explanation.get("positive_reasons") or [])[:max_items]
        if pos:
            lines.append("  Positive: %s" % "; ".join(pos))
    top_neg = (explanation.get("top_risk_reasons") or [])[:max_items]
    if top_neg:
        lines.append("  Top risks: %s" % "; ".join(top_neg))
    else:
        neg = (explanation.get("not_recommended_reasons") or [])[:max_items]
        if neg:
            lines.append("  Risks/Trade-offs: %s" % "; ".join(neg))
    acts = (explanation.get("next_actions") or [])[:max_items]
    if acts:
        lines.append("  Next actions: %s" % "; ".join(acts))
    return "\n".join(lines) if lines else ""


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
