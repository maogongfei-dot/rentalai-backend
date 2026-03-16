# 房源推荐解释引擎：根据评分生成用户可读的推荐说明
# Module7 Phase1-A1：Explain Engine 基础解释框架
# Phase1-A4：字段兼容 + 文案细化
# Phase2-A1：原因排序与重点提炼
# Phase2-A2：场景化解释模板
# Phase2-A3：Why / Why Not 双向解释
# Phase2-A4：可复用展示层格式化
# Phase3-A1：结果摘要输出到 State / Result Layer
# Phase3-A2：多房源 / 多结果对比解释层
# Phase3-A3：TopN 推荐理由汇总层


def _empty_explanation():
    """返回标准解释结构的空模板。Phase2-A3: 新增 why_recommend, why_not_recommend, proceed_with_caution, decision_blockers。"""
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
        "explanation_mode": "",
        "why_recommend": [],
        "why_not_recommend": [],
        "proceed_with_caution": [],
        "decision_blockers": [],
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


# ---------- Phase2-A4: 格式化层辅助函数 ----------

def _limit_items(items, max_items=2):
    """限制列表长度，空值过滤。"""
    lst = _safe_list(items)
    return [x for x in lst if isinstance(x, str) and x.strip()][:max_items]


def _bool_to_recommendation(value):
    """recommended -> API 用 recommendation 字符串。"""
    if value is True:
        return "yes"
    if value is False:
        return "no"
    return "neutral"


def _bool_to_decision_signal(value):
    """recommended -> Agent 用 decision_signal。"""
    if value is True:
        return "positive"
    if value is False:
        return "negative"
    return "mixed"


def _join_cli_section(title: str, items: list, bullet: str = "-") -> str:
    """拼接 CLI section：标题 + 每行 bullet。空 items 返回空字符串。"""
    lst = [x for x in (items or []) if isinstance(x, str) and x.strip()]
    if not lst:
        return ""
    lines = [title + ":"]
    for x in lst:
        lines.append("  %s %s" % (bullet, x))
    return "\n".join(lines)


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
    """根据 explanation 生成一句话 decision_focus。Phase2-A2: 由模板函数替代，此函数作回退。"""
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


# ---------- Phase2-A2: 场景化解释模板 ----------

def _has_risk_keyword(reasons: list, keywords: tuple) -> bool:
    """检查 reasons 中是否有任一包含 keywords 中任一关键词。"""
    if not reasons:
        return False
    for r in reasons:
        if not isinstance(r, str):
            continue
        rn = _normalize_text(r)
        if any(kw in rn for kw in keywords):
            return True
    return False


def _build_house_summary_template(explanation: dict, data: dict) -> str:
    """房源场景化 summary：租房顾问风格。"""
    if not explanation or not isinstance(explanation, dict):
        return "Insufficient data for a detailed evaluation; consider adding more property details."
    rec = explanation.get("recommended")
    top_pos = explanation.get("top_positive_reasons") or []
    top_neg = explanation.get("top_risk_reasons") or []
    pos = explanation.get("positive_reasons") or []
    neg = explanation.get("not_recommended_reasons") or []
    final_f = _to_float(_get_first_value(data, ["final_score", "score", "total_score"]))

    # 强推荐型
    if rec is True and (len(top_pos) > len(top_neg) or (final_f is not None and final_f >= 70)):
        return (
            "This property looks like a strong overall option. It performs well across the main decision factors "
            "and may be worth moving forward on quickly if it matches your practical needs."
        )
    # 谨慎型 / 不推荐型
    if rec is False or (len(top_neg) > len(top_pos) and len(neg) >= 2) or (final_f is not None and final_f < 50):
        return (
            "This property appears less convincing overall. Unless it offers a specific personal advantage, "
            "it would be safer to compare other options before committing."
        )
    # 权衡型
    if rec is None or (pos and neg):
        return (
            "This property has a mixed profile. There are some clear advantages, but also a few trade-offs "
            "that should be checked carefully before making a final decision."
        )
    # 无数据
    if not pos and not neg and final_f is None:
        return "Insufficient data for a detailed evaluation; consider adding more property details."
    # 默认
    return (
        "This property has a mixed profile. There are some clear advantages, but also a few trade-offs "
        "that should be checked carefully before making a final decision."
    )


def _build_risk_summary_template(explanation: dict, data: dict) -> str:
    """合同/风险场景化 summary：合同顾问风格。"""
    if not explanation or not isinstance(explanation, dict):
        return "Consider the key factors before making a decision."
    rec = explanation.get("recommended")
    top_neg = explanation.get("top_risk_reasons") or []
    top_pos = explanation.get("top_positive_reasons") or []
    neg = explanation.get("not_recommended_reasons") or []
    risk_level = _normalize_text(
        _get_first_value(data, ["overall_risk_level", "severity", "risk_level", "overall_risk"])
    )
    if not risk_level:
        score = _get_first_value(data, ["risk_score", "structured_risk_score"])
        v = _to_float(score)
        if v is not None:
            risk_level = "high" if v >= 7 else ("medium" if v >= 4 else "low")
    missing = _safe_list(data.get("missing_clauses"))
    has_major_issues = bool(missing) or len(top_neg) >= 2

    # 高风险型
    if risk_level == "high" or (rec is False and has_major_issues):
        return (
            "This contract or dispute situation contains several meaningful risks. It would be safer to pause "
            "and clarify the key issues before proceeding any further."
        )
    # 可处理但需谨慎型
    if risk_level == "medium" or (rec is None and (top_neg or top_pos)):
        return (
            "This situation is not necessarily unmanageable, but it does require careful review. The key clauses, "
            "evidence, and next steps should be checked in an organized way."
        )
    # 低风险 / 待确认型
    if risk_level in {"low", "none", ""} or (not top_neg and top_pos):
        return (
            "No major red flag is immediately obvious from the current result, but the remaining clauses and "
            "obligations should still be verified before treating the situation as fully safe."
        )
    return (
        "This situation is not necessarily unmanageable, but it does require careful review. The key clauses, "
        "evidence, and next steps should be checked in an organized way."
    )


def _build_house_decision_focus_template(explanation: dict, data: dict) -> str:
    """房源场景化 decision_focus：租房顾问一句话提醒。"""
    if not explanation or not isinstance(explanation, dict):
        return "Consider the key factors before making a decision."
    top_neg = explanation.get("top_risk_reasons") or []
    top_pos = explanation.get("top_positive_reasons") or []
    rec = explanation.get("recommended")
    neg_text = " ".join(_normalize_text(r) for r in top_neg)

    # 价格问题突出
    if _has_risk_keyword(top_neg, ("price", "rent", "high")):
        return "The main decision issue is whether the pricing is still acceptable once the weaker cost factors are taken into account."
    # 通勤问题突出
    if _has_risk_keyword(top_neg, ("commute", "inconvenient")):
        return "The key question is whether the commute trade-off is realistic for your daily routine."
    # 地区匹配问题突出
    if _has_risk_keyword(top_neg, ("area", "weaker")):
        return "The main focus should be whether this location truly fits your target area and lifestyle priorities."
    # 整体较强
    if rec is True and top_pos and len(top_pos) >= len(top_neg):
        return "The main decision focus is whether you want to move quickly on a property that already performs well across the key factors."
    # 混合型
    if top_pos or top_neg:
        return "The key decision is whether this property's strengths are strong enough to outweigh its trade-offs."
    return "Consider the key factors before making a decision."


def _build_risk_decision_focus_template(explanation: dict, data: dict) -> str:
    """风险场景化 decision_focus：合同顾问一句话提醒。"""
    if not explanation or not isinstance(explanation, dict):
        return "Consider the key factors before making a decision."
    top_neg = explanation.get("top_risk_reasons") or []
    rec = explanation.get("recommended")
    missing = _safe_list(data.get("missing_clauses"))
    evidence_list = _safe_list(data.get("evidence_required")) or _safe_list(data.get("evidence_needed"))

    # 缺失条款突出
    if missing or _has_risk_keyword(top_neg, ("missing", "clauses")):
        return "The key issue is to get the missing clauses clarified in writing before relying on this agreement."
    # 押金/维修/解约/涨租问题突出
    if _has_risk_keyword(top_neg, ("deposit", "repair", "termination", "rent increase", "notice")):
        return "The main focus should be on clarifying the highest-risk contract terms before moving forward."
    # 证据问题突出
    if evidence_list or _has_risk_keyword(top_neg, ("evidence", "insufficient")):
        return "The key priority is to organize evidence early so your position is stronger if the dispute escalates."
    # 中风险综合型
    if rec is None and top_neg:
        return "The main focus is to verify the uncertain clauses and prepare a clear action path."
    # 低风险型
    if rec is not False and (not top_neg or len(top_neg) <= 1):
        return "The key step is to confirm the remaining details before treating the situation as safe."
    # 高风险默认
    return "The key issue is to clarify the major contractual risks before you proceed any further."


# ---------- Phase2-A3: Why / Why Not 双向解释 ----------

def _build_why_recommend(explanation: dict, explanation_type: str) -> list:
    """生成 why_recommend：为什么值得继续。"""
    if not explanation or not isinstance(explanation, dict):
        return []
    out = []
    seen = set()
    top_pos = explanation.get("top_positive_reasons") or []
    top_neg = explanation.get("top_risk_reasons") or []
    rec = explanation.get("recommended")
    mode = (explanation.get("explanation_mode") or "").strip()

    def _add(s):
        if s and s not in seen:
            seen.add(s)
            out.append(s)

    if explanation_type == "house":
        if _has_risk_keyword(top_pos, ("competitive", "price", "rent")):
            _add("The pricing appears relatively competitive compared with the overall evaluation.")
        if _has_risk_keyword(top_pos, ("convenient", "commute")):
            _add("The commute or location profile is supportive of day-to-day convenience.")
        if _has_risk_keyword(top_pos, ("area", "good", "quality")):
            _add("The area or location fit aligns well with typical priorities.")
        if rec is True and top_pos:
            _add("The property performs well across practical decision factors.")
        if mode == "strong_recommendation":
            _add("The overall balance of the property is stronger than many average options.")
        if rec is False and top_pos:
            _add("There are still some positive factors worth considering.")
    else:
        if top_pos:
            _add("The issues have already been identified clearly.")
        if top_pos:
            _add("There is at least a basic action path available.")
        if _has_risk_keyword(top_pos, ("legal", "basis", "references")):
            _add("Legal basis or supporting direction is already visible.")
        if _has_risk_keyword(top_pos, ("evidence", "helpful", "prepare")):
            _add("Some risks may still be manageable with clarification and evidence.")
        if rec is not False and top_pos:
            _add("The situation may be workable with proper preparation.")
    return out[:4]


def _build_why_not_recommend(explanation: dict, explanation_type: str) -> list:
    """生成 why_not_recommend：为什么不建议继续。"""
    if not explanation or not isinstance(explanation, dict):
        return []
    out = []
    seen = set()
    top_neg = explanation.get("top_risk_reasons") or []
    top_pos = explanation.get("top_positive_reasons") or []
    rec = explanation.get("recommended")

    def _add(s):
        if s and s not in seen:
            seen.add(s)
            out.append(s)

    if explanation_type == "house":
        if _has_risk_keyword(top_neg, ("price", "rent", "high")):
            _add("The rent level may reduce overall value for money.")
        if _has_risk_keyword(top_neg, ("commute", "inconvenient")):
            _add("The commute trade-off may be too weak for daily use.")
        if _has_risk_keyword(top_neg, ("area", "weaker")):
            _add("The area or location fit may not align well with your target priorities.")
        if _has_risk_keyword(top_neg, ("bills", "unclear")):
            _add("The cost structure may still need closer checking.")
        if rec is False and top_neg:
            _add("The overall profile suggests caution before committing.")
        if rec is True and top_neg:
            _add("There are still some trade-offs to verify.")
    else:
        if _has_risk_keyword(top_neg, ("missing", "clauses")):
            _add("Important clauses may be missing or unclear.")
        if _has_risk_keyword(top_neg, ("deposit", "repair", "termination", "unclear", "risky")):
            _add("The current wording may expose you to legal or practical risk.")
        if _has_risk_keyword(top_neg, ("evidence", "insufficient")):
            _add("Evidence may be too weak if the dispute escalates.")
        if top_neg:
            _add("The contract terms may need clarification before relying on them.")
        if rec is False:
            _add("The risk level suggests pausing before proceeding.")
    return out[:4]


def _build_proceed_with_caution(explanation: dict, data: dict, explanation_type: str) -> list:
    """生成 proceed_with_caution：如果继续，最该注意什么。"""
    if not explanation or not isinstance(explanation, dict):
        return []
    out = []
    seen = set()
    next_actions = explanation.get("next_actions") or []
    top_neg = explanation.get("top_risk_reasons") or []

    def _add(s):
        if s and s not in seen:
            seen.add(s)
            out.append(s)

    if explanation_type == "house":
        if _has_risk_keyword(top_neg, ("bills", "unclear")):
            _add("Confirm the full bills structure before making a decision.")
        if _has_risk_keyword(top_neg, ("commute", "inconvenient")):
            _add("Test the real commute during peak time.")
        if _has_risk_keyword(top_neg, ("price", "rent")):
            _add("Compare this listing with similar options nearby.")
        if _has_risk_keyword(top_neg, ("area", "weaker")):
            _add("Verify whether the area truly matches your personal priorities.")
        for a in next_actions[:2]:
            if isinstance(a, str) and a.strip():
                _add(a)
    else:
        if _has_risk_keyword(top_neg, ("deposit", "repair", "termination", "rent increase")):
            _add("Clarify the highest-risk clauses in writing.")
        if _has_risk_keyword(top_neg, ("evidence",)):
            _add("Organize supporting evidence before challenging the issue.")
        _add("Review deposit, repair, termination, and rent increase terms carefully.")
        _add("Do not rely on vague wording without written confirmation.")
        for a in next_actions[:2]:
            if isinstance(a, str) and a.strip():
                _add(a)
    return out[:4]


def _build_decision_blockers(explanation: dict, data: dict, explanation_type: str) -> list:
    """生成 decision_blockers：当前最主要的阻塞问题。"""
    if not explanation or not isinstance(explanation, dict):
        return []
    out = []
    seen = set()
    top_neg = explanation.get("top_risk_reasons") or []
    rec = explanation.get("recommended")

    def _add(s):
        if s and s not in seen:
            seen.add(s)
            out.append(s)

    if explanation_type == "house":
        if _has_risk_keyword(top_neg, ("price", "rent", "high")):
            _add("High rent relative to the overall profile.")
        if _has_risk_keyword(top_neg, ("commute", "inconvenient")):
            _add("Weak commute convenience.")
        if _has_risk_keyword(top_neg, ("area", "weaker")):
            _add("Area mismatch with the target location.")
        if _has_risk_keyword(top_neg, ("bills", "unclear")):
            _add("Unclear cost structure.")
        if rec is None and top_neg:
            _add("Unclear overall value after considering trade-offs.")
    else:
        if _has_risk_keyword(top_neg, ("missing", "clauses")):
            _add("Missing clauses that affect enforceability or clarity.")
        if _has_risk_keyword(top_neg, ("deposit", "repair", "termination")):
            _add("Unclear deposit, repair, or termination responsibility.")
        if _has_risk_keyword(top_neg, ("evidence", "insufficient")):
            _add("Weak evidence position.")
        if _has_risk_keyword(top_neg, ("legal", "risky", "flagged")):
            _add("Significant unresolved legal risk.")
        if rec is False and top_neg:
            _add("Multiple risk factors require clarification before proceeding.")
    return out[:4]


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

    # recommended
    pos_count = len(exp["positive_reasons"])
    neg_count = len(exp["not_recommended_reasons"])
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

    # Phase2-A1: 提炼 top_positive_reasons / top_risk_reasons
    pos_reasons = exp.get("positive_reasons") or []
    neg_reasons = exp.get("not_recommended_reasons") or []
    exp["top_positive_reasons"] = _select_top_reasons(pos_reasons, top_n=3, context="pos", reason_type="house")
    if not exp["top_positive_reasons"] and pos_reasons:
        exp["top_positive_reasons"] = pos_reasons[:3]
    exp["top_risk_reasons"] = _select_top_reasons(neg_reasons, top_n=3, context="neg", reason_type="house")
    if not exp["top_risk_reasons"] and neg_reasons:
        exp["top_risk_reasons"] = neg_reasons[:3]

    # Phase2-A2: 场景化 summary / decision_focus / explanation_mode
    try:
        exp["summary"] = _build_house_summary_template(exp, house)
    except Exception:
        exp["summary"] = "This property has a mixed profile. Consider the key factors before making a decision."
    try:
        exp["decision_focus"] = _build_house_decision_focus_template(exp, house)
    except Exception:
        exp["decision_focus"] = _build_decision_focus(exp, "house")
    # explanation_mode
    if exp["recommended"] is True:
        exp["explanation_mode"] = "strong_recommendation"
    elif exp["recommended"] is False:
        exp["explanation_mode"] = "cautious_option"
    else:
        exp["explanation_mode"] = "balanced_tradeoff"

    # Phase2-A3: 双向解释
    try:
        exp["why_recommend"] = _build_why_recommend(exp, "house")
    except Exception:
        exp["why_recommend"] = []
    try:
        exp["why_not_recommend"] = _build_why_not_recommend(exp, "house")
    except Exception:
        exp["why_not_recommend"] = []
    try:
        exp["proceed_with_caution"] = _build_proceed_with_caution(exp, house, "house")
    except Exception:
        exp["proceed_with_caution"] = []
    try:
        exp["decision_blockers"] = _build_decision_blockers(exp, house, "house")
    except Exception:
        exp["decision_blockers"] = []

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

    # recommended（模板需要，先算）
    pos_count = len(exp["positive_reasons"])
    neg_count = len(exp["not_recommended_reasons"])
    issues_count = neg_count
    if risk_level == "high":
        exp["recommended"] = False
    elif risk_level == "medium":
        exp["recommended"] = None
    elif risk_level in {"low", "none", ""}:
        if neg_count > pos_count:
            exp["recommended"] = False
        elif pos_count > neg_count:
            exp["recommended"] = True
        else:
            exp["recommended"] = None
    else:
        if neg_count > pos_count:
            exp["recommended"] = False
        elif pos_count > neg_count:
            exp["recommended"] = True
        else:
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

    # Phase2-A1: 提炼 top_positive_reasons / top_risk_reasons
    pos_reasons = exp.get("positive_reasons") or []
    neg_reasons = exp.get("not_recommended_reasons") or []
    exp["top_risk_reasons"] = _select_top_reasons(neg_reasons, top_n=3, context="neg", reason_type="risk")
    if not exp["top_risk_reasons"] and neg_reasons:
        exp["top_risk_reasons"] = neg_reasons[:3]
    exp["top_positive_reasons"] = _select_top_reasons(pos_reasons, top_n=3, context="pos", reason_type="risk")
    if not exp["top_positive_reasons"] and pos_reasons:
        exp["top_positive_reasons"] = pos_reasons[:3]

    # Phase2-A2: 场景化 summary / decision_focus / explanation_mode
    try:
        exp["summary"] = _build_risk_summary_template(exp, risk_result)
    except Exception:
        exp["summary"] = "This situation requires careful review. Consider the key factors before proceeding."
    try:
        exp["decision_focus"] = _build_risk_decision_focus_template(exp, risk_result)
    except Exception:
        exp["decision_focus"] = _build_decision_focus(exp, "risk")
    # explanation_mode
    if risk_level == "high" or exp["recommended"] is False:
        exp["explanation_mode"] = "high_risk"
    elif risk_level == "medium" or (exp["recommended"] is None and neg_reasons):
        exp["explanation_mode"] = "manageable_with_caution"
    else:
        exp["explanation_mode"] = "low_risk_check"

    # Phase2-A3: 双向解释
    try:
        exp["why_recommend"] = _build_why_recommend(exp, "risk")
    except Exception:
        exp["why_recommend"] = []
    try:
        exp["why_not_recommend"] = _build_why_not_recommend(exp, "risk")
    except Exception:
        exp["why_not_recommend"] = []
    try:
        exp["proceed_with_caution"] = _build_proceed_with_caution(exp, risk_result, "risk")
    except Exception:
        exp["proceed_with_caution"] = []
    try:
        exp["decision_blockers"] = _build_decision_blockers(exp, risk_result, "risk")
    except Exception:
        exp["decision_blockers"] = []

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


def format_explanation_for_cli(explanation: dict, max_items: int = 2) -> str:
    """可复用 CLI 展示：将 explanation dict 转为适合命令行的简洁文本。Phase2-A4。"""
    if not explanation or not isinstance(explanation, dict):
        return ""
    parts = []
    summary = (explanation.get("summary") or "").strip()
    if summary:
        parts.append("Summary: %s" % summary)
    rec = explanation.get("recommended")
    rec_str = "Yes" if rec is True else ("No" if rec is False else "Neutral")
    parts.append("Recommendation: %s" % rec_str)
    mode = (explanation.get("explanation_mode") or "").strip()
    if mode:
        parts.append("Mode: %s" % mode)
    focus = (explanation.get("decision_focus") or "").strip()
    if focus:
        parts.append("Decision Focus: %s" % focus)
    why_rec = _join_cli_section("Why Recommend", _limit_items(explanation.get("why_recommend") or [], max_items))
    if why_rec:
        parts.append(why_rec)
    why_not = _join_cli_section("Why Not Recommend", _limit_items(explanation.get("why_not_recommend") or [], max_items))
    if why_not:
        parts.append(why_not)
    blockers = _join_cli_section("Decision Blockers", _limit_items(explanation.get("decision_blockers") or [], max_items))
    if blockers:
        parts.append(blockers)
    caution = _join_cli_section("Proceed With Caution", _limit_items(explanation.get("proceed_with_caution") or [], max_items))
    if caution:
        parts.append(caution)
    actions = _join_cli_section("Next Actions", _limit_items(explanation.get("next_actions") or [], max_items))
    if actions:
        parts.append(actions)
    return "\n\n".join(parts) if parts else ""


def format_explanation_for_api(explanation: dict) -> dict:
    """可复用 API 展示：返回适合 API/前端消费的稳定 dict。Phase2-A4。"""
    if not explanation or not isinstance(explanation, dict):
        return {"summary": "", "recommendation": "neutral", "mode": "", "decision_focus": ""}
    rec = explanation.get("recommended")
    return {
        "summary": (explanation.get("summary") or "").strip(),
        "recommendation": _bool_to_recommendation(rec),
        "mode": (explanation.get("explanation_mode") or "").strip(),
        "decision_focus": (explanation.get("decision_focus") or "").strip(),
        "why_recommend": _limit_items(explanation.get("why_recommend") or [], 4),
        "why_not_recommend": _limit_items(explanation.get("why_not_recommend") or [], 4),
        "decision_blockers": _limit_items(explanation.get("decision_blockers") or [], 4),
        "proceed_with_caution": _limit_items(explanation.get("proceed_with_caution") or [], 4),
        "next_actions": _limit_items(explanation.get("next_actions") or [], 4),
    }


def format_explanation_for_agent(explanation: dict) -> dict:
    """可复用 Agent 展示：返回适合 Agent/Planner 处理的摘要结构。Phase2-A4。"""
    if not explanation or not isinstance(explanation, dict):
        return {"decision_signal": "mixed", "mode": "", "summary": "", "focus": "", "key_positives": [], "key_risks": [], "blockers": [], "suggested_actions": []}
    rec = explanation.get("recommended")
    why_rec = explanation.get("why_recommend") or []
    top_pos = explanation.get("top_positive_reasons") or []
    why_not = explanation.get("why_not_recommend") or []
    top_neg = explanation.get("top_risk_reasons") or []
    blockers = explanation.get("decision_blockers") or []
    caution = explanation.get("proceed_with_caution") or []
    actions = explanation.get("next_actions") or []
    key_positives = _limit_items(why_rec if why_rec else top_pos, 4)
    key_risks = _limit_items(why_not if why_not else top_neg, 4)
    suggested = list(caution)[:2]
    for a in actions:
        if a and a not in suggested:
            suggested.append(a)
    suggested = _limit_items(suggested, 4)
    return {
        "decision_signal": _bool_to_decision_signal(rec),
        "mode": (explanation.get("explanation_mode") or "").strip(),
        "summary": (explanation.get("summary") or "").strip(),
        "focus": (explanation.get("decision_focus") or "").strip(),
        "key_positives": key_positives,
        "key_risks": key_risks,
        "blockers": _limit_items(blockers, 4),
        "suggested_actions": suggested,
    }


# ---------- Phase3-A1: 结果层快照 ----------

def build_explanation_snapshot(explanation: dict) -> dict:
    """基于 explanation 构建轻量、稳定、可保存的摘要快照。Phase3-A1。"""
    if not explanation or not isinstance(explanation, dict):
        return {
            "summary": "",
            "recommendation": "neutral",
            "mode": "",
            "decision_focus": "",
            "key_positives": [],
            "key_risks": [],
            "blockers": [],
            "suggested_actions": [],
        }
    rec = explanation.get("recommended")
    why_rec = explanation.get("why_recommend") or []
    top_pos = explanation.get("top_positive_reasons") or []
    why_not = explanation.get("why_not_recommend") or []
    top_neg = explanation.get("top_risk_reasons") or []
    blockers = explanation.get("decision_blockers") or []
    caution = explanation.get("proceed_with_caution") or []
    actions = explanation.get("next_actions") or []
    key_positives = _limit_items(why_rec if why_rec else top_pos, 3)
    key_risks = _limit_items(why_not if why_not else top_neg, 3)
    suggested = list(caution)[:2]
    for a in actions:
        if isinstance(a, str) and a.strip() and a not in suggested:
            suggested.append(a)
    suggested = _limit_items(suggested, 3)
    return {
        "summary": (explanation.get("summary") or "").strip(),
        "recommendation": _bool_to_recommendation(rec),
        "mode": (explanation.get("explanation_mode") or "").strip(),
        "decision_focus": (explanation.get("decision_focus") or "").strip(),
        "key_positives": key_positives,
        "key_risks": key_risks,
        "blockers": _limit_items(blockers, 3),
        "suggested_actions": suggested,
    }


def attach_explanation_snapshot(result: dict, explanation_key: str = "explanation", snapshot_key: str = "explanation_summary") -> dict:
    """为 result 追加 explanation_summary。若有 explanation 则生成快照，否则不报错。Phase3-A1。"""
    if not result or not isinstance(result, dict):
        return result
    expl = result.get(explanation_key)
    if not expl or not isinstance(expl, dict):
        return result
    try:
        result[snapshot_key] = build_explanation_snapshot(expl)
    except Exception:
        result[snapshot_key] = {
            "summary": "",
            "recommendation": "neutral",
            "mode": "",
            "decision_focus": "",
            "key_positives": [],
            "key_risks": [],
            "blockers": [],
            "suggested_actions": [],
        }
    return result


def format_explanation_summary_for_cli(explanation_summary: dict, max_items: int = 2) -> str:
    """从 explanation_summary 生成简洁 CLI 文本。Phase3-A1。"""
    if not explanation_summary or not isinstance(explanation_summary, dict):
        return ""
    parts = []
    summary = (explanation_summary.get("summary") or "").strip()
    if summary:
        parts.append("Summary: %s" % summary)
    rec = (explanation_summary.get("recommendation") or "neutral").strip()
    parts.append("Recommendation: %s" % rec)
    focus = (explanation_summary.get("decision_focus") or "").strip()
    if focus:
        parts.append("Decision Focus: %s" % focus)
    key_pos = _limit_items(explanation_summary.get("key_positives") or [], max_items)
    if key_pos:
        parts.append(_join_cli_section("Key Positives", key_pos))
    key_risks = _limit_items(explanation_summary.get("key_risks") or [], max_items)
    if key_risks:
        parts.append(_join_cli_section("Key Risks", key_risks))
    return "\n\n".join(parts) if parts else ""


# ---------- Phase3-A2: 多结果对比解释层 ----------

def _empty_comparison_explanation(comparison_type: str = "house") -> dict:
    """返回标准对比解释结构的空模板。Phase3-A2。"""
    return {
        "comparison_type": comparison_type,
        "winner": "",
        "loser": "",
        "summary": "",
        "decision_focus": "",
        "winner_advantages": [],
        "loser_drawbacks": [],
        "key_differences": [],
        "recommended_action": "",
    }


def _get_score_value(data, keys, default=None):
    """从 dict 中按 keys 顺序取第一个存在的数值。兼容嵌套 scores。"""
    if not data or not isinstance(data, dict):
        return default
    for k in keys:
        v = data.get(k)
        if v is not None:
            f = _to_float(v)
            if f is not None:
                return f
    scores = data.get("scores")
    if isinstance(scores, dict):
        for k in keys:
            v = scores.get(k)
            if v is not None:
                f = _to_float(v)
                if f is not None:
                    return f
    return default


def _risk_rank_value(data) -> float:
    """风险越高返回值越大。用于比较：值大=更危险。"""
    if not data or not isinstance(data, dict):
        return 0.0
    level = _normalize_text(
        _get_first_value(data, ["overall_risk_level", "severity", "risk_level", "overall_risk"])
    )
    if level in ("high", "critical"):
        return 10.0
    if level in ("medium", "moderate"):
        return 5.0
    if level in ("low", "none", ""):
        return 1.0
    score = _get_first_value(data, ["risk_score", "structured_risk_score"])
    v = _to_float(score)
    if v is not None:
        return float(v)
    return 0.0


def _normalize_recommendation_from_summary(explanation_summary: dict) -> int:
    """从 explanation_summary 的 recommendation 转为可比较数值：yes=2, neutral=1, no=0。"""
    if not explanation_summary or not isinstance(explanation_summary, dict):
        return 1
    rec = (explanation_summary.get("recommendation") or "neutral").strip().lower()
    if rec == "yes":
        return 2
    if rec == "no":
        return 0
    return 1


def _build_comparison_decision_focus(comparison_type: str, close: bool) -> str:
    """生成对比决策焦点文案。Phase3-A2。"""
    if comparison_type == "house":
        if close:
            return "The key decision is whether the weaker option offers any personal advantage that justifies its trade-offs."
        return "The main focus should be whether the score gap reflects your real priorities."
    if comparison_type == "risk":
        if close:
            return "The key focus is whether the higher-risk option can realistically be clarified before you proceed."
        return "The main decision issue is which situation leaves you with fewer unresolved legal risks."
    return ""


def compare_house_results(
    primary: dict,
    secondary: dict,
    primary_label: str = "Option A",
    secondary_label: str = "Option B",
) -> dict:
    """比较两个房源结果，输出为什么一个优于另一个。Phase3-A2。"""
    out = _empty_comparison_explanation("house")
    out["winner"] = primary_label
    out["loser"] = secondary_label

    score_keys = ["final_score", "score", "total_score"]
    s1 = _get_score_value(primary, score_keys)
    s2 = _get_score_value(secondary, score_keys)

    # 若 primary 分数更低，则交换 winner/loser
    if s1 is not None and s2 is not None:
        if s1 < s2:
            primary, secondary = secondary, primary
            primary_label, secondary_label = secondary_label, primary_label
            s1, s2 = s2, s1
            out["winner"] = primary_label
            out["loser"] = secondary_label
    elif s1 is None and s2 is not None:
        primary, secondary = secondary, primary
        primary_label, secondary_label = secondary_label, primary_label
        out["winner"] = primary_label
        out["loser"] = secondary_label
    elif s1 is None and s2 is None:
        # 回退到 explanation_summary / explanation 的 recommendation
        sum1 = primary.get("explanation_summary") or primary.get("explanation") or {}
        sum2 = secondary.get("explanation_summary") or secondary.get("explanation") or {}
        r1 = _normalize_recommendation_from_summary(sum1 if isinstance(sum1, dict) else {})
        r2 = _normalize_recommendation_from_summary(sum2 if isinstance(sum2, dict) else {})
        if r1 < r2:
            primary, secondary = secondary, primary
            primary_label, secondary_label = secondary_label, primary_label
            out["winner"] = primary_label
            out["loser"] = secondary_label
        elif r1 == r2:
            # 比较分项 score
            dims = ["price_score", "commute_score", "area_score", "bills_score", "bedrooms_score"]
            t1 = sum(_get_score_value(primary, [d]) or 0 for d in dims)
            t2 = sum(_get_score_value(secondary, [d]) or 0 for d in dims)
            if t1 < t2:
                primary, secondary = secondary, primary
                primary_label, secondary_label = secondary_label, primary_label
                out["winner"] = primary_label
                out["loser"] = secondary_label

    # 判断是否接近
    close = False
    if s1 is not None and s2 is not None:
        gap = abs(s1 - s2)
        close = gap < 5.0  # 5 分以内视为接近

    # 构建 winner_advantages / loser_drawbacks / key_differences
    adv = []
    drw = []
    diffs = []

    sum_win = primary.get("explanation_summary") or primary.get("explanation") or {}
    sum_los = secondary.get("explanation_summary") or secondary.get("explanation") or {}
    sum_win = sum_win if isinstance(sum_win, dict) else {}
    sum_los = sum_los if isinstance(sum_los, dict) else {}

    if s1 is not None and s2 is not None:
        if s1 > s2:
            adv.append("Better overall score")
        if close:
            adv.append("Slightly better overall profile")
    if not adv:
        adv.append("Stronger overall profile")

    pos_win = _safe_list(sum_win.get("key_positives") or sum_win.get("why_recommend") or sum_win.get("top_positive_reasons"))
    pos_los = _safe_list(sum_los.get("key_positives") or sum_los.get("why_recommend") or sum_los.get("top_positive_reasons"))
    neg_los = _safe_list(sum_los.get("key_risks") or sum_los.get("why_not_recommend") or sum_los.get("top_risk_reasons"))
    neg_win = _safe_list(sum_win.get("key_risks") or sum_win.get("why_not_recommend") or sum_win.get("top_risk_reasons"))

    for p in pos_win[:2]:
        if isinstance(p, str) and p.strip():
            adv.append(p[:80] if len(p) > 80 else p)
    for n in neg_los[:2]:
        if isinstance(n, str) and n.strip():
            drw.append(n[:80] if len(n) > 80 else n)
    if not drw:
        drw.append("Weaker price-to-value balance")
        drw.append("More trade-offs in the overall profile")

    # 分项差异
    dim_labels = {
        "price_score": ("price", "rent"),
        "commute_score": ("commute",),
        "area_score": ("area",),
        "bills_score": ("bills",),
        "bedrooms_score": ("bedrooms",),
    }
    for dim, labels in dim_labels.items():
        v1 = _get_score_value(primary, [dim]) or 0
        v2 = _get_score_value(secondary, [dim]) or 0
        if v1 > v2 and (v1 - v2) > 2:
            lbl = labels[0].capitalize()
            diffs.append(f"{primary_label} has a stronger {lbl} score, while {secondary_label} is weaker on {lbl} fit.")
    if not diffs:
        diffs.append(f"{primary_label} shows better overall balance between cost and convenience.")
        if close:
            diffs.append(f"{secondary_label} may still be viable, but it has more compromises.")

    out["winner_advantages"] = _limit_items(adv, 3)
    out["loser_drawbacks"] = _limit_items(drw, 3)
    out["key_differences"] = _limit_items(diffs, 3)

    if close:
        out["summary"] = f"The two options are relatively close, but {primary_label} has a slightly better overall profile."
    else:
        out["summary"] = f"{primary_label} appears stronger overall because it performs better across the main decision factors."

    out["decision_focus"] = _build_comparison_decision_focus("house", close)

    if close:
        out["recommended_action"] = "Compare both options against your personal non-negotiables before deciding."
    else:
        out["recommended_action"] = f"Prioritize viewing {primary_label} first, then keep {secondary_label} as a backup if needed."

    return out


def compare_risk_results(
    primary: dict,
    secondary: dict,
    primary_label: str = "Risk A",
    secondary_label: str = "Risk B",
) -> dict:
    """比较两个风险分析结果，判断哪个更可控。winner=更可控，loser=更高风险。Phase3-A2。"""
    out = _empty_comparison_explanation("risk")
    r1 = _risk_rank_value(primary)
    r2 = _risk_rank_value(secondary)

    # 风险越低越优，所以 r 小的是 winner
    if r1 > r2:
        out["winner"] = secondary_label
        out["loser"] = primary_label
        primary, secondary = secondary, primary
        primary_label, secondary_label = secondary_label, primary_label
        r1, r2 = r2, r1
    else:
        out["winner"] = primary_label
        out["loser"] = secondary_label

    close = abs(r1 - r2) < 2.0 if (r1 is not None and r2 is not None) else False

    adv = []
    drw = []
    diffs = []

    sum_win = primary.get("explanation_summary") or primary.get("explanation") or {}
    sum_los = secondary.get("explanation_summary") or secondary.get("explanation") or {}
    sum_win = sum_win if isinstance(sum_win, dict) else {}
    sum_los = sum_los if isinstance(sum_los, dict) else {}

    adv.append("Fewer serious red flags")
    adv.append("More manageable action path")
    for p in _safe_list(sum_win.get("key_positives") or sum_win.get("why_recommend"))[:2]:
        if isinstance(p, str) and p.strip():
            adv.append(p[:80])
    drw.append("More missing clauses")
    drw.append("Higher legal uncertainty")
    for n in _safe_list(sum_los.get("key_risks") or sum_los.get("why_not_recommend"))[:2]:
        if isinstance(n, str) and n.strip():
            drw.append(n[:80])

    diffs.append(f"{out['loser']} has more clause-level uncertainty.")
    diffs.append(f"{out['winner']} still has issues, but they appear more manageable.")
    if close:
        diffs.append("One option has a clearer action path than the other.")

    out["winner_advantages"] = _limit_items(adv, 3)
    out["loser_drawbacks"] = _limit_items(drw, 3)
    out["key_differences"] = _limit_items(diffs, 3)

    if close:
        out["summary"] = f"Both situations contain risk, but {out['winner']} looks more manageable based on the current result."
    else:
        out["summary"] = f"{out['loser']} appears more serious overall because it contains more unresolved contractual concerns."

    out["decision_focus"] = _build_comparison_decision_focus("risk", close)

    if close:
        out["recommended_action"] = "Clarify the higher-risk clauses before relying on the weaker option."
    else:
        out["recommended_action"] = "Treat the lower-risk option as the safer path unless new evidence changes the picture."

    return out


def build_house_ranking_explanations(results: list) -> list:
    """为 TopN 房源结果生成简短排名解释。Phase3-A2。"""
    if not results or not isinstance(results, list):
        return []
    out = []
    for i, r in enumerate(results[:5]):  # 最多 5 个
        note = ""
        if i == 0:
            note = "Why it ranks first: strongest overall profile across the main decision factors."
        elif i == 1:
            note = "Why it trails the first option: slightly weaker on key factors compared with the top choice."
        else:
            note = f"Main trade-offs compared with top option: ranks #{i + 1} with more compromises."
        rec = dict(r) if isinstance(r, dict) else {}
        rec["ranking_explanation"] = note
        rec["comparison_note"] = note
        out.append(rec)
    return out


def format_comparison_for_cli(comparison: dict, max_items: int = 2) -> str:
    """将 comparison explanation 转为 CLI 文本。Phase3-A2。"""
    if not comparison or not isinstance(comparison, dict):
        return ""
    parts = []
    summary = (comparison.get("summary") or "").strip()
    if summary:
        parts.append("Comparison Summary: %s" % summary)
    winner = (comparison.get("winner") or "").strip()
    loser = (comparison.get("loser") or "").strip()
    if winner:
        parts.append("Winner: %s" % winner)
    if loser:
        parts.append("Loser: %s" % loser)
    focus = (comparison.get("decision_focus") or "").strip()
    if focus:
        parts.append("Decision Focus: %s" % focus)
    adv = _limit_items(comparison.get("winner_advantages") or [], max_items)
    if adv:
        parts.append(_join_cli_section("Winner Advantages", adv))
    drw = _limit_items(comparison.get("loser_drawbacks") or [], max_items)
    if drw:
        parts.append(_join_cli_section("Loser Drawbacks", drw))
    action = (comparison.get("recommended_action") or "").strip()
    if action:
        parts.append("Recommended Action: %s" % action)
    return "\n\n".join(parts) if parts else ""


# ---------- Phase3-A3: TopN 推荐理由汇总层 ----------

def _empty_ranking_summary() -> dict:
    """返回 TopN 排名汇总结构的空模板。Phase3-A3。"""
    return {
        "summary": "",
        "top_pick": "",
        "backup_pick": "",
        "ranking_logic": "",
        "overall_decision_focus": "",
        "top_reasons": [],
        "backup_reasons": [],
        "caution_reasons": [],
        "recommended_action": "",
        "items": [],
    }


def _house_score_for_sort(r: dict) -> float:
    """从房源结果取总分用于排序。"""
    v = _get_score_value(r, ["final_score", "score", "total_score"])
    if v is not None:
        return float(v)
    dims = ["price_score", "commute_score", "area_score", "bills_score", "bedrooms_score"]
    return sum(_get_score_value(r, [d]) or 0 for d in dims)


def _build_ranking_explanation_for_rank(r: dict, rank: int, label: str, total: int) -> str:
    """为指定 rank 的房源生成一句 ranking_explanation。Phase3-A3。"""
    sum_data = r.get("explanation_summary") or r.get("explanation") or {}
    sum_data = sum_data if isinstance(sum_data, dict) else {}
    rec = (sum_data.get("recommendation") or "neutral").strip().lower()
    mode = (sum_data.get("mode") or "").strip()
    pos = _safe_list(sum_data.get("key_positives") or sum_data.get("why_recommend") or sum_data.get("top_positive_reasons"))
    neg = _safe_list(sum_data.get("key_risks") or sum_data.get("why_not_recommend") or sum_data.get("top_risk_reasons"))

    if rank == 1:
        if rec == "yes" and pos:
            return "This option ranks first because it shows the strongest overall balance across the main decision factors."
        return "This property stands out as the strongest current choice based on score, overall fit, and fewer trade-offs."
    if rank == 2:
        if neg:
            return "This option remains viable as a backup, but it trails the top choice in overall balance or practical fit."
        return "This property is still worth considering, though it comes with more trade-offs than the leading option."
    # rank >= 3
    if total == 3 and rank == 3:
        return "This option is less compelling at the moment because the overall profile is weaker than the stronger alternatives."
    return "This property may still work for specific personal reasons, but it currently ranks behind the stronger options."


def build_top_house_summary(
    results: list,
    labels: list | None = None,
    top_n: int = 3,
) -> dict:
    """输入一组房源结果，输出 TopN 推荐理由汇总。Phase3-A3。"""
    out = _empty_ranking_summary()
    if not results or not isinstance(results, list):
        return out

    # 若未排序，按 score 排序
    sorted_results = sorted(
        [r for r in results if isinstance(r, dict)],
        key=_house_score_for_sort,
        reverse=True,
    )
    top_items = sorted_results[:top_n]
    n = len(top_items)
    if n == 0:
        return out

    # 生成 labels
    if labels and len(labels) >= n:
        item_labels = [str(labels[i]).strip() or f"Option {i + 1}" for i in range(n)]
    else:
        item_labels = [r.get("house_label") or r.get("label") or f"Option {i + 1}" for i, r in enumerate(top_items)]

    # 为每个 item 生成 ranking_explanation 和 role
    items = []
    for i, r in enumerate(top_items):
        rank = i + 1
        label = item_labels[i] if i < len(item_labels) else f"Option {rank}"
        role = "top_pick" if rank == 1 else ("backup" if rank == 2 else "lower_priority")
        expl = _build_ranking_explanation_for_rank(r, rank, label, n)
        rec = dict(r) if isinstance(r, dict) else {}
        rec["rank"] = rank
        rec["ranking_explanation"] = expl
        rec["ranking_role"] = role
        rec["label"] = label
        items.append({
            "label": label,
            "rank": rank,
            "ranking_explanation": expl,
            "role": role,
        })
    out["items"] = items

    # summary
    if n == 1:
        out["summary"] = f"Among the current options, {item_labels[0]} stands out as the strongest overall choice."
    elif n == 2:
        out["summary"] = f"Among the current top options, {item_labels[0]} stands out as the strongest overall choice, while {item_labels[1]} remains a reasonable backup."
    else:
        out["summary"] = "The current ranking shows a clear first choice, a usable backup option, and one weaker option with more trade-offs."

    out["top_pick"] = item_labels[0] if n >= 1 else ""
    out["backup_pick"] = item_labels[1] if n >= 2 else ""

    out["ranking_logic"] = "The ranking is mainly driven by overall score, practical balance, and the relative strength of trade-offs."

    if n >= 2:
        out["overall_decision_focus"] = "The key decision is whether the top-ranked option also matches your personal non-negotiables in real life."
    else:
        out["overall_decision_focus"] = "The main focus should be whether this option matches your personal priorities before proceeding."

    # top_reasons: 第1名优点
    r1 = top_items[0]
    sum1 = r1.get("explanation_summary") or r1.get("explanation") or {}
    sum1 = sum1 if isinstance(sum1, dict) else {}
    top_reasons = _safe_list(sum1.get("key_positives") or sum1.get("why_recommend") or sum1.get("top_positive_reasons"))
    out["top_reasons"] = _limit_items([x for x in top_reasons if isinstance(x, str) and x.strip()], 3)

    # backup_reasons: 第2名保留原因
    if n >= 2:
        r2 = top_items[1]
        sum2 = r2.get("explanation_summary") or r2.get("explanation") or {}
        sum2 = sum2 if isinstance(sum2, dict) else {}
        backup_reasons = _safe_list(sum2.get("key_positives") or sum2.get("why_recommend") or sum2.get("top_positive_reasons"))
        out["backup_reasons"] = _limit_items([x for x in backup_reasons if isinstance(x, str) and x.strip()], 2)
    if not out["backup_reasons"] and n >= 2:
        out["backup_reasons"] = ["Still viable as a backup option.", "Worth considering if the top choice does not work out."]

    # caution_reasons: 第2/3名风险点
    caution = []
    for i in range(1, min(n, 3)):
        ri = top_items[i]
        sumi = ri.get("explanation_summary") or ri.get("explanation") or {}
        sumi = sumi if isinstance(sumi, dict) else {}
        negs = _safe_list(sumi.get("key_risks") or sumi.get("why_not_recommend") or sumi.get("top_risk_reasons"))
        for x in negs[:2]:
            if isinstance(x, str) and x.strip() and x not in caution:
                caution.append(x)
    out["caution_reasons"] = _limit_items(caution, 3)
    if not out["caution_reasons"] and n >= 2:
        out["caution_reasons"] = ["Lower-ranked options have more trade-offs.", "Consider whether the weaker profile fits your priorities."]

    if n >= 3:
        out["recommended_action"] = "View the top-ranked option first, keep the second option as backup, and only pursue the weaker option if it offers a specific personal advantage."
    elif n >= 2:
        out["recommended_action"] = "Prioritize the strongest option, then compare the backup choice against your non-negotiables before moving further."
    else:
        out["recommended_action"] = "Proceed with the top-ranked option and verify it matches your personal priorities."

    return out


def format_top_house_summary_for_cli(summary_data: dict, max_items: int = 2) -> str:
    """将 TopN 汇总转为 CLI 文本。Phase3-A3。"""
    if not summary_data or not isinstance(summary_data, dict):
        return ""
    parts = []
    summary = (summary_data.get("summary") or "").strip()
    if summary:
        parts.append("Ranking Summary: %s" % summary)
    top_pick = (summary_data.get("top_pick") or "").strip()
    if top_pick:
        parts.append("Top Pick: %s" % top_pick)
    backup_pick = (summary_data.get("backup_pick") or "").strip()
    if backup_pick:
        parts.append("Backup Pick: %s" % backup_pick)
    focus = (summary_data.get("overall_decision_focus") or "").strip()
    if focus:
        parts.append("Overall Decision Focus: %s" % focus)
    top_reasons = _limit_items(summary_data.get("top_reasons") or [], max_items)
    if top_reasons:
        parts.append(_join_cli_section("Top Reasons", top_reasons))
    caution = _limit_items(summary_data.get("caution_reasons") or [], max_items)
    if caution:
        parts.append(_join_cli_section("Caution Reasons", caution))
    action = (summary_data.get("recommended_action") or "").strip()
    if action:
        parts.append("Recommended Action: %s" % action)
    items = summary_data.get("items") or []
    if items:
        lines = ["Per-item Ranking Notes:"]
        for it in items[:5]:
            lbl = (it.get("label") or "").strip()
            expl = (it.get("ranking_explanation") or "").strip()
            if lbl and expl:
                lines.append("  %s: %s" % (lbl, expl))
        if len(lines) > 1:
            parts.append("\n".join(lines))
    return "\n\n".join(parts) if parts else ""


def attach_top_house_summary_to_results(results: list, summary_data: dict) -> list:
    """将 summary_data 中的 items 信息附加到 results 前 top_n 项。Phase3-A3。不修改原 results，返回新列表。"""
    if not results or not isinstance(results, list):
        return list(results) if results else []
    items = summary_data.get("items") or []
    out = []
    for i, r in enumerate(results):
        rec = dict(r) if isinstance(r, dict) else {}
        if i < len(items):
            it = items[i]
            rec["rank"] = it.get("rank", i + 1)
            rec["ranking_explanation"] = it.get("ranking_explanation", "")
            rec["ranking_role"] = it.get("role", "lower_priority")
        out.append(rec)
    return out


if __name__ == "__main__":
    # 房源解释示例
    sample_house = {
        "price_score": 85,
        "commute_score": 70,
        "area_score": 55,
    }
    house_result = explain_house(sample_house)
    print("=== House explanation (raw) ===\n", house_result)

    # Phase2-A4: 三种格式化输出
    print("\n=== format_explanation_for_cli (house) ===")
    print(format_explanation_for_cli(house_result))
    print("\n=== format_explanation_for_api (house) ===")
    print(format_explanation_for_api(house_result))
    print("\n=== format_explanation_for_agent (house) ===")
    print(format_explanation_for_agent(house_result))

    # 合同风险解释示例
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
        "missing_clauses": [{"clause_type": "termination_clause", "status": "missing"}],
        "weak_clauses": [{"clause_type": "repair_clause", "status": "weak"}],
    }
    risk_result = build_risk_explanation(sample_risk)
    print("\n=== Risk explanation (raw) ===\n", risk_result)

    print("\n=== format_explanation_for_cli (risk) ===")
    print(format_explanation_for_cli(risk_result))
    print("\n=== format_explanation_for_api (risk) ===")
    print(format_explanation_for_api(risk_result))
    print("\n=== format_explanation_for_agent (risk) ===")
    print(format_explanation_for_agent(risk_result))

    # Phase3-A1: explanation_summary 示例
    print("\n=== Phase3-A1: build_explanation_snapshot (house) ===")
    house_snapshot = build_explanation_snapshot(house_result)
    print(house_snapshot)

    print("\n=== Phase3-A1: build_explanation_snapshot (risk) ===")
    risk_snapshot = build_explanation_snapshot(risk_result)
    print(risk_snapshot)

    print("\n=== Phase3-A1: attach_explanation_snapshot ===")
    sample_result = {"explanation": house_result, "score": 75}
    attach_explanation_snapshot(sample_result)
    print("Keys:", list(sample_result.keys()))
    print("explanation_summary:", sample_result.get("explanation_summary"))

    # Phase3-A2: 多结果对比解释示例
    print("\n=== Phase3-A2: compare_house_results ===")
    house_a = {"final_score": 82, "price_score": 85, "commute_score": 78, "area_score": 80}
    house_b = {"final_score": 72, "price_score": 70, "commute_score": 65, "area_score": 75}
    house_a["explanation_summary"] = build_explanation_snapshot(explain_house(house_a))
    house_b["explanation_summary"] = build_explanation_snapshot(explain_house(house_b))
    comp_house = compare_house_results(house_a, house_b, "Rank 1", "Rank 2")
    print(comp_house)
    print("\n--- format_comparison_for_cli (house) ---")
    print(format_comparison_for_cli(comp_house))

    print("\n=== Phase3-A2: compare_risk_results ===")
    risk_a = {"overall_risk_level": "high", "risk_score": 8}
    risk_b = {"overall_risk_level": "medium", "structured_risk_score": 4}
    risk_a["explanation_summary"] = build_explanation_snapshot(build_risk_explanation(risk_a))
    risk_b["explanation_summary"] = build_explanation_snapshot(build_risk_explanation(risk_b))
    comp_risk = compare_risk_results(risk_a, risk_b, "Contract A", "Contract B")
    print(comp_risk)
    print("\n--- format_comparison_for_cli (risk) ---")
    print(format_comparison_for_cli(comp_risk))

    print("\n=== Phase3-A2: build_house_ranking_explanations ===")
    ranked = [house_a, house_b, {"final_score": 65, "price_score": 60}]
    with_notes = build_house_ranking_explanations(ranked)
    for i, r in enumerate(with_notes[:3]):
        print(f"  #{i+1}: {r.get('comparison_note', '')}")

    # Phase3-A3: TopN 推荐理由汇总示例
    print("\n=== Phase3-A3: build_top_house_summary ===")
    house_c = {"final_score": 65, "price_score": 60, "commute_score": 55, "area_score": 50}
    house_c["explanation_summary"] = build_explanation_snapshot(explain_house(house_c))
    top3 = [house_a, house_b, house_c]
    top_summary = build_top_house_summary(top3, labels=["Rank 1", "Rank 2", "Rank 3"], top_n=3)
    print("summary:", top_summary.get("summary"))
    print("top_pick:", top_summary.get("top_pick"))
    print("backup_pick:", top_summary.get("backup_pick"))
    expl_preview = lambda it: (it.get("ranking_explanation") or "")[:50] + ("..." if len(it.get("ranking_explanation") or "") > 50 else "")
    print("items:", [(it.get("label"), it.get("role"), expl_preview(it)) for it in top_summary.get("items", [])])
    print("\n--- format_top_house_summary_for_cli ---")
    print(format_top_house_summary_for_cli(top_summary))
