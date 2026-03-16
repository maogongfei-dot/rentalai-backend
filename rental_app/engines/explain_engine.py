# 房源推荐解释引擎：根据评分生成用户可读的推荐说明
# Module7 Explain Engine - 完整收口 (Phase5-A4)
#
# 模块结构索引：
# 1. Base helpers        - _empty_explanation, _empty_unified_decision, _get_first_value, _safe_list, _limit_items, ...
# 2. Single explanation  - explain_house, build_risk_explanation, build_explanation
# 3. Explanation format  - format_explanation_for_cli, format_explanation_for_api, format_explanation_for_agent
# 4. Snapshot / result   - build_explanation_snapshot, attach_explanation_snapshot
# 5. Comparison / rank   - compare_house_results, compare_risk_results, build_top_house_summary, format_top_house_summary_for_cli
# 6. Final recommendation - build_final_house_recommendation, build_final_risk_recommendation, format_final_*_for_cli
# 7. Unified decision    - build_unified_decision, attach_unified_decision, format_unified_decision_for_cli/api/agent
# 8. Payload / protocol  - normalize_unified_decision, export_unified_decision_payload
# 9. Self-check          - run_explain_engine_self_check
#
# ---------- 1. Base helpers ----------


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


# ---------- 2. Single explanation builders ----------

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


# ---------- 3. Explanation formatting ----------

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


# ---------- Phase3-A4: 房源推荐结论层 Final Recommendation Layer ----------

def _empty_final_recommendation() -> dict:
    """返回最终推荐结论结构的空模板。Phase3-A4。"""
    return {
        "final_summary": "",
        "primary_recommendation": {},
        "backup_recommendation": {},
        "lower_priority_options": [],
        "decision_confidence": "medium",
        "final_decision_focus": "",
        "final_action": "",
        "supporting_reasons": [],
        "watchouts": [],
    }


def _build_primary_reason(r: dict, label: str) -> str:
    """为首选生成 reason 文案。"""
    sum_data = r.get("explanation_summary") or r.get("explanation") or {}
    sum_data = sum_data if isinstance(sum_data, dict) else {}
    summary = (sum_data.get("summary") or "").strip()
    pos = _safe_list(sum_data.get("key_positives") or sum_data.get("why_recommend"))
    rank_expl = (r.get("ranking_explanation") or "").strip()
    rec = (sum_data.get("recommendation") or "neutral").strip().lower()

    if rec == "yes" and pos:
        return "This option is the strongest current choice because it offers the best overall balance with fewer major trade-offs."
    if summary and len(summary) > 20:
        # 取 summary 首句或前 100 字作为参考，但生成结论性文案
        return "This option is the strongest current choice because it offers the best overall balance with fewer major trade-offs."
    if rank_expl:
        return rank_expl
    return "This option is the strongest current choice based on score, overall fit, and fewer trade-offs."


def _build_backup_reason(r: dict, label: str, primary_score: float | None) -> str:
    """为备选生成 reason 文案。"""
    sum_data = r.get("explanation_summary") or r.get("explanation") or {}
    sum_data = sum_data if isinstance(sum_data, dict) else {}
    pos = _safe_list(sum_data.get("key_positives") or sum_data.get("why_recommend"))
    neg = _safe_list(sum_data.get("key_risks") or sum_data.get("why_not_recommend"))

    if pos and neg:
        return "This option remains a reasonable backup, but it is weaker than the leading choice in overall balance or fit."
    if neg:
        return "This option remains viable as a backup, though it has more trade-offs than the top choice."
    return "This option remains a reasonable backup, but it trails the leading choice in overall balance or practical fit."


def _build_lower_priority_reason(r: dict, label: str, rank: int) -> str:
    """为 lower_priority 生成 reason 文案。"""
    rank_expl = (r.get("ranking_explanation") or "").strip()
    if rank_expl:
        return rank_expl[:120] + ("..." if len(rank_expl) > 120 else "")
    sum_data = r.get("explanation_summary") or r.get("explanation") or {}
    sum_data = sum_data if isinstance(sum_data, dict) else {}
    neg = _safe_list(sum_data.get("key_risks") or sum_data.get("why_not_recommend"))
    if neg:
        return "This option currently ranks lower because its overall profile involves more trade-offs than the stronger alternatives."
    return "This property may still suit a specific personal need, but it is not the strongest option under the current evaluation."


def _compute_decision_confidence(
    top_items: list,
    score_gap: float,
    sum1: dict,
    sum2: dict | None,
) -> str:
    """计算 decision_confidence: high / medium / low。"""
    rec1 = (sum1.get("recommendation") or "neutral").strip().lower()
    mode1 = (sum1.get("mode") or "").strip().lower()
    neg1 = _safe_list(sum1.get("key_risks") or sum1.get("why_not_recommend"))

    # low: 整体都不强
    if rec1 == "no" or "caution" in mode1 or "mixed" in mode1 or "tradeoff" in mode1:
        if len(neg1) >= 2:
            return "low"
    if score_gap is not None and score_gap < 3 and len(top_items) >= 2:
        if sum2:
            neg2 = _safe_list(sum2.get("key_risks") or sum2.get("why_not_recommend"))
            if len(neg1) >= 1 and len(neg2) >= 1:
                return "low"

    # high: 第1名明显领先
    if score_gap is not None and score_gap >= 10:
        if rec1 == "yes" and len(neg1) <= 1:
            return "high"
    if rec1 == "yes" and not neg1 and score_gap is not None and score_gap >= 5:
        return "high"

    # medium: 默认
    return "medium"


def build_final_house_recommendation(
    results: list,
    labels: list | None = None,
    top_n: int = 3,
) -> dict:
    """输入一组房源结果，输出最终推荐结论。Phase3-A4。"""
    out = _empty_final_recommendation()
    if not results or not isinstance(results, list):
        return out

    # 复用 top_house_summary 的排序逻辑
    sorted_results = sorted(
        [r for r in results if isinstance(r, dict)],
        key=_house_score_for_sort,
        reverse=True,
    )
    top_items = sorted_results[:top_n]
    n = len(top_items)
    if n == 0:
        return out

    # labels
    if labels and len(labels) >= n:
        item_labels = [str(labels[i]).strip() or f"Option {i + 1}" for i in range(n)]
    else:
        item_labels = [r.get("house_label") or r.get("label") or f"Option {i + 1}" for i, r in enumerate(top_items)]

    s1 = _get_score_value(top_items[0], ["final_score", "score", "total_score"])
    s2 = _get_score_value(top_items[1], ["final_score", "score", "total_score"]) if n >= 2 else None
    score_gap = (s1 - s2) if (s1 is not None and s2 is not None) else None

    sum1 = top_items[0].get("explanation_summary") or top_items[0].get("explanation") or {}
    sum1 = sum1 if isinstance(sum1, dict) else {}
    sum2 = (top_items[1].get("explanation_summary") or top_items[1].get("explanation") or {}) if n >= 2 else None
    sum2 = sum2 if isinstance(sum2, dict) else {} if sum2 else {}

    # primary_recommendation
    out["primary_recommendation"] = {
        "label": item_labels[0],
        "reason": _build_primary_reason(top_items[0], item_labels[0]),
        "score": s1,
    }

    # backup_recommendation
    if n >= 2:
        out["backup_recommendation"] = {
            "label": item_labels[1],
            "reason": _build_backup_reason(top_items[1], item_labels[1], s1),
            "score": s2,
        }
    else:
        out["backup_recommendation"] = {}

    # lower_priority_options
    out["lower_priority_options"] = []
    for i in range(2, n):
        r = top_items[i]
        label = item_labels[i] if i < len(item_labels) else f"Option {i + 1}"
        out["lower_priority_options"].append({
            "label": label,
            "reason": _build_lower_priority_reason(r, label, i + 1),
        })

    # final_summary
    if n == 1:
        out["final_summary"] = f"{item_labels[0]} stands out as the clearest current recommendation."
    elif score_gap is not None and score_gap >= 8:
        out["final_summary"] = f"{item_labels[0]} stands out as the clearest current recommendation, with {item_labels[1]} serving as the main backup and the remaining options falling behind on overall fit."
    elif score_gap is not None and score_gap < 5 and n >= 2:
        out["final_summary"] = f"The top two options are relatively close, but {item_labels[0]} still holds a slight edge as the stronger overall recommendation."
    else:
        rec1 = (sum1.get("recommendation") or "neutral").strip().lower()
        if rec1 == "no" or len(_safe_list(sum1.get("key_risks") or [])) >= 2:
            out["final_summary"] = f"None of the current options looks particularly strong, but {item_labels[0]} is the least compromised choice among the available results."
        else:
            out["final_summary"] = f"{item_labels[0]} stands out as the clearest current recommendation, with {item_labels[1]} serving as the main backup." if n >= 2 else f"{item_labels[0]} stands out as the clearest current recommendation."

    # decision_confidence
    out["decision_confidence"] = _compute_decision_confidence(top_items, score_gap, sum1, sum2 if n >= 2 else None)

    # final_decision_focus
    if out["decision_confidence"] == "high":
        out["final_decision_focus"] = "The key decision now is whether the top-ranked option also matches your real non-negotiables in practice."
    elif out["decision_confidence"] == "low":
        out["final_decision_focus"] = "The main focus should be whether any of these options can realistically meet your must-haves before you proceed."
    else:
        out["final_decision_focus"] = "The main focus should be whether the stronger option's advantages are enough to justify moving quickly."

    # final_action
    if n >= 3:
        out["final_action"] = "View the primary option first, keep the backup ready, and only revisit lower-ranked options if new information changes the picture."
    elif n >= 2:
        out["final_action"] = "Compare the top two options against your personal must-haves before making a final commitment."
    else:
        out["final_action"] = "Proceed with the primary option and verify it matches your personal priorities in person."

    # supporting_reasons
    pos1 = _safe_list(sum1.get("key_positives") or sum1.get("why_recommend") or sum1.get("top_positive_reasons"))
    out["supporting_reasons"] = _limit_items([x for x in pos1 if isinstance(x, str) and x.strip()], 3)

    # watchouts
    watchouts = []
    neg1 = _safe_list(sum1.get("key_risks") or sum1.get("why_not_recommend") or sum1.get("top_risk_reasons"))
    for x in neg1[:2]:
        if isinstance(x, str) and x.strip():
            watchouts.append(x)
    caution = _safe_list(sum1.get("proceed_with_caution") or sum1.get("next_actions"))
    for x in caution[:1]:
        if isinstance(x, str) and x.strip() and x not in watchouts:
            watchouts.append(x)
    if n >= 2 and not watchouts:
        watchouts.append("The backup option has more trade-offs than the primary choice.")
    out["watchouts"] = _limit_items(watchouts, 3)

    return out


def format_final_recommendation_for_cli(data: dict, max_items: int = 2) -> str:
    """将最终推荐结论转为 CLI 文本。Phase3-A4。"""
    if not data or not isinstance(data, dict):
        return ""
    parts = []
    summary = (data.get("final_summary") or "").strip()
    if summary:
        parts.append("Final Summary: %s" % summary)

    primary = data.get("primary_recommendation") or {}
    if primary and primary.get("label"):
        line = "Primary Recommendation: %s" % primary.get("label")
        if primary.get("score") is not None:
            line += " (score: %s)" % primary.get("score")
        parts.append(line)
        if primary.get("reason"):
            parts.append("  Reason: %s" % primary.get("reason"))

    backup = data.get("backup_recommendation") or {}
    if backup and backup.get("label"):
        line = "Backup Recommendation: %s" % backup.get("label")
        if backup.get("score") is not None:
            line += " (score: %s)" % backup.get("score")
        parts.append(line)
        if backup.get("reason"):
            parts.append("  Reason: %s" % backup.get("reason"))

    conf = (data.get("decision_confidence") or "medium").strip()
    parts.append("Confidence: %s" % conf)

    focus = (data.get("final_decision_focus") or "").strip()
    if focus:
        parts.append("Decision Focus: %s" % focus)

    supporting = _limit_items(data.get("supporting_reasons") or [], max_items)
    if supporting:
        parts.append(_join_cli_section("Supporting Reasons", supporting))

    watchouts = _limit_items(data.get("watchouts") or [], max_items)
    if watchouts:
        parts.append(_join_cli_section("Watchouts", watchouts))

    action = (data.get("final_action") or "").strip()
    if action:
        parts.append("Final Action: %s" % action)

    return "\n\n".join(parts) if parts else ""


# ---------- Phase4-A1: Risk Final Recommendation Layer ----------

def _empty_risk_final_recommendation() -> dict:
    """返回 Risk Final Recommendation 结构的空模板。Phase4-A1。"""
    return {
        "final_summary": "",
        "safer_option": {},
        "higher_risk_option": {},
        "manageable_path": "",
        "decision_confidence": "medium",
        "final_decision_focus": "",
        "final_action": "",
        "supporting_reasons": [],
        "watchouts": [],
    }


def _risk_level_str(data: dict) -> str:
    """从 risk result 取 risk_level 字符串。"""
    if not data or not isinstance(data, dict):
        return ""
    level = _normalize_text(
        _get_first_value(data, ["overall_risk_level", "severity", "risk_level", "overall_risk"])
    )
    if level in ("high", "critical"):
        return "high"
    if level in ("medium", "moderate"):
        return "medium"
    if level in ("low", "none", ""):
        return "low"
    score = _get_first_value(data, ["risk_score", "structured_risk_score"])
    v = _to_float(score)
    if v is not None:
        if v >= 7:
            return "high"
        if v >= 4:
            return "medium"
        return "low"
    return "medium"


def _risk_blocker_count(data: dict) -> int:
    """统计 risk result 中的 blockers / issues 数量。"""
    if not data or not isinstance(data, dict):
        return 0
    expl = data.get("explanation_summary") or data.get("explanation") or {}
    expl = expl if isinstance(expl, dict) else {}
    blockers = _safe_list(expl.get("blockers") or expl.get("decision_blockers"))
    issues = _safe_list(data.get("risk_flags") or data.get("issues"))
    missing = _safe_list(data.get("missing_clauses"))
    weak = _safe_list(data.get("weak_clauses"))
    return len(blockers) + len(issues) + len(missing) + len(weak)


def build_final_risk_recommendation(result: dict, label: str = "Current Case") -> dict:
    """对单个 risk result 输出最终处理结论。Phase4-A1。"""
    out = _empty_risk_final_recommendation()
    if not result or not isinstance(result, dict):
        return out

    level = _risk_level_str(result)
    sum_data = result.get("explanation_summary") or result.get("explanation") or {}
    sum_data = sum_data if isinstance(sum_data, dict) else {}

    # 单风险时 safer_option 表示当前 case 的可控程度
    if level == "high":
        out["final_summary"] = "This case currently looks too risky to proceed without clarification."
        out["manageable_path"] = "Pause and clarify the highest-risk points before relying on the current contract or position."
        out["final_action"] = "Collect evidence, identify the highest-risk clauses, and seek written clarification before proceeding."
        out["safer_option"] = {
            "label": label,
            "reason": "This case requires clarification before it can be considered manageable.",
            "risk_level": level,
        }
        out["higher_risk_option"] = {}
    elif level == "medium":
        out["final_summary"] = "This case may still be manageable, but it should not be treated as safe without further checking."
        out["manageable_path"] = "Work through the unclear clauses and supporting evidence in an organized way."
        out["final_action"] = "Review the key clauses, prepare evidence, and clarify any vague wording before moving forward."
        out["safer_option"] = {
            "label": label,
            "reason": "This case can be managed with careful review and clarification of the unclear points.",
            "risk_level": level,
        }
        out["higher_risk_option"] = {}
    else:
        out["final_summary"] = "No severe red flag is obvious at the moment, but the remaining details should still be verified."
        out["manageable_path"] = "Proceed carefully while confirming the remaining contractual details."
        out["final_action"] = "Confirm the remaining details in writing and keep basic records in case the situation changes."
        out["safer_option"] = {
            "label": label,
            "reason": "This case appears relatively manageable, but verification of details is still recommended.",
            "risk_level": level,
        }
        out["higher_risk_option"] = {}

    # decision_confidence
    blockers = _risk_blocker_count(result)
    if level == "high" and blockers >= 3:
        out["decision_confidence"] = "high"
    elif level == "low" and blockers <= 1:
        out["decision_confidence"] = "high"
    elif level == "medium" or blockers >= 2:
        out["decision_confidence"] = "medium"
    else:
        out["decision_confidence"] = "medium"

    out["final_decision_focus"] = "The key focus is whether the unresolved clauses can be clarified before you rely on this position."
    out["supporting_reasons"] = _limit_items(
        _safe_list(sum_data.get("key_positives") or sum_data.get("why_recommend")),
        3
    )
    out["watchouts"] = _limit_items(
        _safe_list(sum_data.get("key_risks") or sum_data.get("why_not_recommend") or sum_data.get("blockers") or sum_data.get("decision_blockers")),
        3
    )
    if not out["watchouts"] and level != "low":
        out["watchouts"] = ["Verify unclear clauses before relying on the current position."]

    return out


def _compute_risk_decision_confidence(
    safer_rank: float,
    higher_rank: float,
    n: int,
) -> str:
    """计算 risk comparison 的 decision_confidence。"""
    if n <= 1:
        return "medium"
    gap = higher_rank - safer_rank
    if gap >= 4:
        return "high"
    if gap < 2:
        return "low"
    return "medium"


def build_final_risk_comparison_recommendation(
    results: list,
    labels: list | None = None,
) -> dict:
    """对多个风险结果输出最终结论，判断哪个更可控。Phase4-A1。"""
    out = _empty_risk_final_recommendation()
    if not results or not isinstance(results, list):
        return out

    valid = [r for r in results if isinstance(r, dict)]
    if not valid:
        return out

    # 构建 (result, label) 对，按风险从低到高排序
    if labels and len(labels) >= len(valid):
        pairs = [(valid[i], str(labels[i]).strip() or f"Risk Option {i + 1}") for i in range(len(valid))]
    else:
        pairs = [(r, r.get("label") or f"Risk Option {i + 1}") for i, r in enumerate(valid)]
    pairs.sort(key=lambda p: _risk_rank_value(p[0]))
    sorted_results = [p[0] for p in pairs]
    item_labels = [p[1] for p in pairs]
    n = len(sorted_results)

    safer = sorted_results[0]
    safer_label = item_labels[0]
    safer_level = _risk_level_str(safer)
    safer_rank = _risk_rank_value(safer)

    out["safer_option"] = {
        "label": safer_label,
        "reason": "This option appears more manageable because it contains fewer severe red flags and a clearer action path.",
        "risk_level": safer_level,
    }
    sum_safer = safer.get("explanation_summary") or safer.get("explanation") or {}
    sum_safer = sum_safer if isinstance(sum_safer, dict) else {}
    pos = _safe_list(sum_safer.get("key_positives") or sum_safer.get("why_recommend"))
    if pos:
        out["safer_option"]["reason"] = pos[0][:100] + ("..." if len(pos[0]) > 100 else "") if isinstance(pos[0], str) else out["safer_option"]["reason"]

    if n >= 2:
        higher = sorted_results[-1]
        higher_label = item_labels[-1]
        higher_level = _risk_level_str(higher)
        higher_rank = _risk_rank_value(higher)

        out["higher_risk_option"] = {
            "label": higher_label,
            "reason": "This option remains weaker because it carries more unresolved contractual uncertainty and a less secure path forward.",
            "risk_level": higher_level,
        }
        sum_higher = higher.get("explanation_summary") or higher.get("explanation") or {}
        sum_higher = sum_higher if isinstance(sum_higher, dict) else {}
        neg = _safe_list(sum_higher.get("key_risks") or sum_higher.get("why_not_recommend"))
        if neg:
            out["higher_risk_option"]["reason"] = neg[0][:100] + ("..." if len(neg[0]) > 100 else "") if isinstance(neg[0], str) else out["higher_risk_option"]["reason"]

        gap = higher_rank - safer_rank
        if gap >= 4:
            out["final_summary"] = f"{safer_label} is the safer current path, while {higher_label} contains more significant unresolved concerns."
        elif higher_level == "high" and safer_level != "high":
            out["final_summary"] = f"None of the current risk scenarios looks especially comfortable, but {safer_label} is still the less risky path."
        elif safer_level in ("low", "medium") and higher_level in ("low", "medium"):
            out["final_summary"] = f"Both scenarios appear relatively manageable, though {safer_label} still offers the cleaner path overall."
        else:
            out["final_summary"] = f"{safer_label} is the safer current path, while {higher_label} carries more risk."

        out["decision_confidence"] = _compute_risk_decision_confidence(safer_rank, higher_rank, n)
        out["manageable_path"] = "Take the safer path first, preserve all evidence, and do not rely on unclear wording without written confirmation."
        out["final_decision_focus"] = "The main decision issue is which option leaves you with fewer unresolved legal and practical risks."
        out["final_action"] = "Take the safer path first, preserve all evidence, and do not rely on unclear wording without written confirmation."
        out["supporting_reasons"] = _limit_items(
            _safe_list(sum_safer.get("key_positives") or sum_safer.get("why_recommend")),
            3
        )
        out["watchouts"] = _limit_items(
            _safe_list(sum_higher.get("key_risks") or sum_higher.get("why_not_recommend") or sum_higher.get("blockers") or sum_higher.get("decision_blockers")),
            3
        )
        if not out["watchouts"]:
            out["watchouts"] = ["The higher-risk option should not be relied upon without clarification."]
    else:
        # 单结果回退到 build_final_risk_recommendation
        return build_final_risk_recommendation(safer, safer_label)

    return out


def format_final_risk_recommendation_for_cli(data: dict, max_items: int = 2) -> str:
    """将 Risk Final Recommendation 转为 CLI 文本。Phase4-A1。"""
    if not data or not isinstance(data, dict):
        return ""
    parts = []
    summary = (data.get("final_summary") or "").strip()
    if summary:
        parts.append("Final Summary: %s" % summary)

    safer = data.get("safer_option") or {}
    if safer and safer.get("label"):
        line = "Safer Option: %s" % safer.get("label")
        if safer.get("risk_level"):
            line += " (risk_level: %s)" % safer.get("risk_level")
        parts.append(line)
        if safer.get("reason"):
            parts.append("  Reason: %s" % safer.get("reason"))

    higher = data.get("higher_risk_option") or {}
    if higher and higher.get("label"):
        line = "Higher Risk Option: %s" % higher.get("label")
        if higher.get("risk_level"):
            line += " (risk_level: %s)" % higher.get("risk_level")
        parts.append(line)
        if higher.get("reason"):
            parts.append("  Reason: %s" % higher.get("reason"))

    path = (data.get("manageable_path") or "").strip()
    if path:
        parts.append("Manageable Path: %s" % path)

    conf = (data.get("decision_confidence") or "medium").strip()
    parts.append("Confidence: %s" % conf)

    focus = (data.get("final_decision_focus") or "").strip()
    if focus:
        parts.append("Decision Focus: %s" % focus)

    supporting = _limit_items(data.get("supporting_reasons") or [], max_items)
    if supporting:
        parts.append(_join_cli_section("Supporting Reasons", supporting))

    watchouts = _limit_items(data.get("watchouts") or [], max_items)
    if watchouts:
        parts.append(_join_cli_section("Watchouts", watchouts))

    action = (data.get("final_action") or "").strip()
    if action:
        parts.append("Final Action: %s" % action)

    return "\n\n".join(parts) if parts else ""


# ---------- Phase4-A2: House + Risk 双结论合并层 Unified Decision Layer ----------

def _empty_unified_decision() -> dict:
    """返回 Unified Decision 结构的空模板。Phase4-A2 / Phase4-A4 / Phase5-A1 / Phase5-A2。"""
    return {
        "overall_recommendation": "unknown",
        "final_summary": "",
        "decision_confidence": "medium",
        "confidence_reason": "",
        "house_signal": "unknown",
        "risk_signal": "unknown",
        "decision_focus": "",
        "primary_blockers": [],
        "supporting_reasons": [],
        "required_actions_before_proceeding": [],
        "final_action": "",
        "missing_information": [],
        "assessment_limitations": [],
        "recommended_inputs_to_improve_decision": [],
        "trace_summary": "",
        "decision_trace": [],
        "house_trace_reasons": [],
        "risk_trace_reasons": [],
        "blocker_trace": [],
        "support_trace": [],
        "user_facing_summary": "",
        "user_facing_reason": [],
        "user_facing_risk_note": [],
        "user_facing_next_step": [],
        "user_facing_explanation": [],
        "house_reference": {},
        "risk_reference": {},
    }


def _detect_missing_house_information(house_final: dict | None) -> list:
    """识别 house 侧缺失信息。Phase4-A4。unknown != bad。"""
    out = []
    if not house_final or not isinstance(house_final, dict):
        out.append("House-side final recommendation is missing.")
        return out
    primary = house_final.get("primary_recommendation") or {}
    score = primary.get("score")
    if score is None:
        s = _get_score_value(house_final, ["final_score", "score", "total_score"])
        if s is None:
            out.append("The overall property score is not available.")
    expl = house_final.get("explanation_summary") or house_final.get("explanation") or {}
    expl = expl if isinstance(expl, dict) else {}
    summary = (expl.get("summary") or "").strip()
    if not summary and not primary:
        out.append("House-side explanation is very limited.")
    return out


def _detect_missing_risk_information(risk_final: dict | None) -> list:
    """识别 risk 侧缺失信息。Phase4-A4。missing != high risk。"""
    out = []
    if not risk_final or not isinstance(risk_final, dict):
        out.append("Risk-side final recommendation is missing.")
        return out
    safer = risk_final.get("safer_option") or {}
    level = (safer.get("risk_level") or "").strip()
    if not level:
        score = _get_first_value(risk_final, ["risk_score", "structured_risk_score"])
        if score is None:
            out.append("No clear contract risk level is available.")
    expl = risk_final.get("explanation_summary") or risk_final.get("explanation") or {}
    expl = expl if isinstance(expl, dict) else {}
    summary = (expl.get("summary") or "").strip()
    if not summary and not safer.get("reason"):
        out.append("Risk-side explanation is very limited.")
    return out


def _build_assessment_limitations(house_final: dict | None, risk_final: dict | None) -> list:
    """构建 assessment_limitations。Phase4-A4。"""
    out = []
    if not house_final:
        out.append("Property value and fit have not been fully evaluated.")
    elif not (house_final.get("primary_recommendation") or {}).get("score") and _get_score_value(house_final, ["final_score", "score"]) is None:
        out.append("Property scoring may be incomplete.")
    if not risk_final:
        out.append("Contract or dispute risk has not been fully assessed.")
    else:
        safer = risk_final.get("safer_option") or {}
        if not safer.get("risk_level"):
            out.append("Clause-level review may be incomplete.")
    return _limit_items(out, 3)


def _build_confidence_reason(
    unified: dict,
    house_final: dict | None,
    risk_final: dict | None,
) -> str:
    """生成 confidence_reason。Phase4-A4。"""
    conf = (unified.get("decision_confidence") or "medium").strip().lower()
    h_sig = (unified.get("house_signal") or "unknown").strip()
    r_sig = (unified.get("risk_signal") or "unknown").strip()
    missing = _safe_list(unified.get("missing_information") or [])

    if conf == "high":
        return "Confidence is high because both property-side and risk-side signals are available and point in a consistent direction."
    if conf == "low":
        if not house_final or not risk_final:
            return "Confidence is low because important parts of the property or risk assessment are still missing."
        if h_sig == "unknown" or r_sig == "unknown":
            return "Confidence is low because one or both sides have not been fully assessed."
        if len(missing) >= 2:
            return "Confidence is low because several key inputs are still missing."
        return "Confidence is low because the system is making a conservative judgment rather than a definitive one."
    # medium
    if h_sig == "unknown" or r_sig == "unknown":
        return "Confidence is medium because the overall direction is visible, but some practical or contractual details still need confirmation."
    return "Confidence is medium because the conclusion is broadly formed, but some details remain to be confirmed."


def _build_recommended_inputs_to_improve_decision(
    house_final: dict | None,
    risk_final: dict | None,
) -> list:
    """生成 recommended_inputs_to_improve_decision。Phase4-A4。"""
    out = []
    if not house_final:
        out.extend([
            "Rent details and total monthly cost",
            "Commute route and travel time",
            "Target area fit and bills structure",
            "Bedroom/layout suitability",
        ])
    if not risk_final:
        out.extend([
            "Deposit clause review",
            "Repair responsibility clarification",
            "Termination and rent increase clause check",
            "Evidence list and written confirmation",
            "Full contract wording review",
        ])
    if house_final and risk_final:
        missing_h = _detect_missing_house_information(house_final)
        missing_r = _detect_missing_risk_information(risk_final)
        if missing_h:
            out.append("Complete property evaluation inputs (score, commute, area fit).")
        if missing_r:
            out.append("Complete contract-risk review (clause-level, evidence).")
    return _limit_items(out, 6)


# ---------- Phase5-A1: Trace Layer 辅助函数 ----------

def _truncate_trace(text: str, max_len: int = 100) -> str:
    """将 trace 文本截断为短句。"""
    if not text or not isinstance(text, str):
        return ""
    s = text.strip()
    if len(s) <= max_len:
        return s
    return s[: max_len - 3].rsplit(".", 1)[0].strip() + "..." if "." in s[: max_len - 3] else s[: max_len - 3] + "..."


def _extract_house_trace_reasons(house_final: dict | None) -> list:
    """从 house_final 提取影响最终结论的房源侧原因。Phase5-A1。"""
    out = []
    seen = set()
    if not house_final or not isinstance(house_final, dict):
        return out

    def _add(s):
        if s and isinstance(s, str) and s.strip():
            t = _truncate_trace(s.strip(), 100)
            if t and t not in seen:
                seen.add(t)
                out.append(t)

    for x in _safe_list(house_final.get("supporting_reasons") or [])[:2]:
        _add(x)
    for x in _safe_list(house_final.get("watchouts") or [])[:2]:
        _add(x)
    primary = house_final.get("primary_recommendation") or {}
    _add(primary.get("reason"))
    summary = (house_final.get("final_summary") or "").strip()
    if summary and len(summary) <= 120:
        _add(summary)
    elif summary:
        _add(summary[:80] + "...")
    expl = house_final.get("explanation_summary") or house_final.get("explanation") or {}
    expl = expl if isinstance(expl, dict) else {}
    for x in _safe_list(expl.get("key_positives") or expl.get("why_recommend"))[:1]:
        _add(x)
    for x in _safe_list(expl.get("key_risks") or expl.get("why_not_recommend"))[:1]:
        _add(x)
    return _limit_items(out, 4)


def _extract_risk_trace_reasons(risk_final: dict | None) -> list:
    """从 risk_final 提取影响最终结论的风险侧原因。Phase5-A1。"""
    out = []
    seen = set()
    if not risk_final or not isinstance(risk_final, dict):
        return out

    def _add(s):
        if s and isinstance(s, str) and s.strip():
            t = _truncate_trace(s.strip(), 100)
            if t and t not in seen:
                seen.add(t)
                out.append(t)

    for x in _safe_list(risk_final.get("supporting_reasons") or [])[:2]:
        _add(x)
    for x in _safe_list(risk_final.get("watchouts") or [])[:2]:
        _add(x)
    summary = (risk_final.get("final_summary") or "").strip()
    if summary:
        _add(summary[:100] + ("..." if len(summary) > 100 else ""))
    path = (risk_final.get("manageable_path") or "").strip()
    if path:
        _add(path[:100] + ("..." if len(path) > 100 else ""))
    safer = risk_final.get("safer_option") or {}
    _add(safer.get("reason"))
    higher = risk_final.get("higher_risk_option") or {}
    _add(higher.get("reason"))
    return _limit_items(out, 4)


def _build_blocker_trace(
    unified: dict,
    house_final: dict | None,
    risk_final: dict | None,
) -> list:
    """构建 blocker_trace：真正阻塞最终决策的原因。Phase5-A1。"""
    out = []
    seen = set()
    blockers = _safe_list(unified.get("primary_blockers") or [])
    for x in blockers[:2]:
        if x and isinstance(x, str) and x.strip():
            t = _truncate_trace(x, 80)
            if t and t not in seen:
                seen.add(t)
                out.append(t)
    if risk_final:
        for x in _safe_list(risk_final.get("watchouts") or [])[:1]:
            if x and isinstance(x, str) and x.strip():
                t = _truncate_trace(x, 80)
                if t and t not in seen:
                    seen.add(t)
                    out.append(t)
    if house_final:
        for x in _safe_list(house_final.get("watchouts") or [])[:1]:
            if x and isinstance(x, str) and x.strip():
                t = _truncate_trace(x, 80)
                if t and t not in seen:
                    seen.add(t)
                    out.append(t)
    missing = _safe_list(unified.get("missing_information") or [])
    if not house_final and not risk_final and missing:
        out.append("Risk-side review is incomplete, so a safe proceed decision is not yet justified.")
    elif not risk_final and house_final and missing:
        out.append("Risk-side review is incomplete, so a safe proceed decision is not yet justified.")
    elif not house_final and risk_final and missing:
        out.append("Property value and fit have not been fully evaluated.")
    return _limit_items(out, 4)


def _build_support_trace(
    unified: dict,
    house_final: dict | None,
    risk_final: dict | None,
) -> list:
    """构建 support_trace：支撑继续推进的原因。Phase5-A1。"""
    out = []
    seen = set()
    supporting = _safe_list(unified.get("supporting_reasons") or [])
    for x in supporting[:2]:
        if x and isinstance(x, str) and x.strip() and x not in seen:
            t = _truncate_trace(x, 80)
            if t:
                seen.add(t)
                out.append(t)
    if house_final:
        for x in _safe_list(house_final.get("supporting_reasons") or [])[:1]:
            if x and x not in seen:
                t = _truncate_trace(x, 80)
                if t:
                    seen.add(t)
                    out.append(t)
    if risk_final:
        for x in _safe_list(risk_final.get("supporting_reasons") or [])[:1]:
            if x and x not in seen:
                t = _truncate_trace(x, 80)
                if t:
                    seen.add(t)
                    out.append(t)
        path = (risk_final.get("manageable_path") or "").strip()
        if path and "path" not in seen:
            t = _truncate_trace(path, 80)
            if t:
                out.append(t)
    return _limit_items(out, 4)


def _build_decision_trace(
    unified: dict,
    house_final: dict | None,
    risk_final: dict | None,
) -> list:
    """构建 decision_trace：顺序化原因链。Phase5-A1。"""
    out = []
    seen = set()
    rec = (unified.get("overall_recommendation") or "unknown").strip()
    h_sig = (unified.get("house_signal") or "unknown").strip()
    r_sig = (unified.get("risk_signal") or "unknown").strip()
    house_reasons = _safe_list(unified.get("house_trace_reasons") or [])
    risk_reasons = _safe_list(unified.get("risk_trace_reasons") or [])
    blockers = _safe_list(unified.get("blocker_trace") or [])
    support = _safe_list(unified.get("support_trace") or [])

    def _add(s):
        if s and isinstance(s, str) and s.strip():
            t = s.strip()[:95]
            if t not in seen:
                seen.add(t)
                out.append(s.strip()[:90] + ("..." if len(s.strip()) > 90 else ""))

    if house_final or house_reasons:
        if h_sig == "positive":
            _add("The property-side signal is positive enough to keep this option under consideration.")
        elif h_sig == "unknown":
            _add("The property-side signal is not yet available.")
        elif house_reasons:
            _add(house_reasons[0])
        else:
            _add("The property-side signal is mixed or weak.")

    if risk_final or risk_reasons:
        if r_sig == "manageable":
            _add("The risk-side signal is manageable with normal checks.")
        elif r_sig == "unknown":
            _add("The risk-side signal is not yet available.")
        elif r_sig in ("caution", "high_risk") and risk_reasons:
            _add(risk_reasons[0])
        else:
            _add("The risk-side signal suggests caution.")

    if blockers:
        _add(blockers[0])
    elif support:
        _add(support[0])

    if rec == "proceed":
        _add("As a result, the current recommendation is to proceed with normal checks.")
    elif rec == "proceed_with_caution":
        _add("As a result, the current recommendation is to proceed with caution.")
    elif rec == "hold_and_clarify":
        _add("As a result, the current recommendation is to hold and clarify before moving forward.")
    elif rec == "not_recommended":
        _add("As a result, the current recommendation is not to proceed with this option.")
    else:
        _add("The overall recommendation is driven by the combined property and risk signals above.")

    return _limit_items(out, 5)


def _build_trace_summary(unified: dict) -> str:
    """生成 trace_summary：一句话概括结论驱动力。Phase5-A1。"""
    rec = (unified.get("overall_recommendation") or "unknown").strip()
    h_sig = (unified.get("house_signal") or "unknown").strip()
    r_sig = (unified.get("risk_signal") or "unknown").strip()
    blockers = _safe_list(unified.get("blocker_trace") or [])
    support = _safe_list(unified.get("support_trace") or [])

    if rec == "proceed":
        return "The final recommendation is mainly driven by a strong property profile and a manageable risk position."
    if rec == "proceed_with_caution":
        return "The property remains viable, but unresolved contract-side concerns are the main reason for a cautious recommendation."
    if rec == "hold_and_clarify":
        if h_sig == "unknown" or r_sig == "unknown":
            return "The current decision is driven by missing information that still needs clarification."
        return "The current decision is driven less by a bad property signal and more by unresolved risks or missing information that still need clarification."
    if rec == "not_recommended":
        return "The overall decision is driven by a weak combined profile, where neither the property case nor the risk position is strong enough."
    return "The final recommendation is driven by the combined property and risk signals above."


# ---------- Phase5-A2: Explain-to-User Layer 辅助函数 ----------

def _build_user_facing_summary(unified: dict) -> str:
    """生成 user_facing_summary：一句最适合直接给用户看的总结。Phase5-A2。"""
    rec = (unified.get("overall_recommendation") or "unknown").strip()
    if rec == "proceed":
        return "This property currently looks reasonable to move forward with, and the main risks appear manageable."
    if rec == "proceed_with_caution":
        return "This property may still be worth pursuing, but you should be careful and confirm a few important points before committing."
    if rec == "hold_and_clarify":
        return "This option is not ready for a confident go-ahead yet. It would be better to clarify the key missing or risky points first."
    if rec == "not_recommended":
        return "This option does not currently look strong enough to justify moving forward, given the trade-offs and unresolved risks."
    return "The current recommendation is still forming; more information would help make a clearer decision."


def _build_user_facing_reason(unified: dict) -> list:
    """生成 user_facing_reason：告诉用户「为什么会这样建议」。Phase5-A2。"""
    out = []
    seen = set()
    rec = (unified.get("overall_recommendation") or "unknown").strip()
    h_sig = (unified.get("house_signal") or "unknown").strip()
    r_sig = (unified.get("risk_signal") or "unknown").strip()
    support = _safe_list(unified.get("supporting_reasons") or [])
    support_trace = _safe_list(unified.get("support_trace") or [])

    def _add(s):
        if s and isinstance(s, str) and s.strip():
            t = s.strip()[:80]
            if t not in seen:
                seen.add(t)
                out.append(s.strip())

    if rec in ("proceed", "proceed_with_caution"):
        if h_sig == "positive":
            _add("The property itself still has some practical strengths.")
        if r_sig in ("manageable", "caution"):
            _add("At the moment, the main concerns seem manageable rather than completely blocking.")
        if support or support_trace:
            _add("The overall value may still make sense if the remaining issues are checked properly.")
    if rec in ("hold_and_clarify", "not_recommended"):
        if h_sig != "weak":
            _add("The current recommendation is not purely negative; it is mainly limited by unresolved details.")
        if support or support_trace:
            _add("Some positive factors remain, but they are outweighed by the unresolved risks or gaps.")
    return _limit_items(out, 4)


def _build_user_facing_risk_note(unified: dict) -> list:
    """生成 user_facing_risk_note：告诉用户「有哪些要注意的风险/不确定点」。Phase5-A2。"""
    out = []
    seen = set()
    blockers = _safe_list(unified.get("blocker_trace") or unified.get("primary_blockers") or [])
    missing = _safe_list(unified.get("missing_information") or [])
    limitations = _safe_list(unified.get("assessment_limitations") or [])

    def _add(s):
        if s and isinstance(s, str) and s.strip():
            t = s.strip()[:70]
            if t not in seen:
                seen.add(t)
                out.append(s.strip())

    for x in blockers[:2]:
        _add(x)
    if missing:
        _add("There may be missing information affecting how reliable the current recommendation is.")
    for x in limitations[:1]:
        _add(x)
    if blockers or missing:
        _add("A few unresolved points still need checking before you rely on this result.")
    if missing and not out:
        _add("The current result should be treated cautiously if the missing inputs are not filled.")
    return _limit_items(out, 4)


def _build_user_facing_next_step(unified: dict) -> list:
    """生成 user_facing_next_step：告诉用户「接下来先做什么」。Phase5-A2。"""
    out = []
    seen = set()
    fa = (unified.get("final_action") or "").strip()
    actions = _safe_list(unified.get("required_actions_before_proceeding") or [])
    rec = (unified.get("overall_recommendation") or "unknown").strip()
    missing = _safe_list(unified.get("missing_information") or [])

    def _add(s):
        if s and isinstance(s, str) and s.strip():
            t = s.strip()[:70]
            if t not in seen:
                seen.add(t)
                out.append(s.strip())

    if fa:
        _add(fa)
    for x in actions[:2]:
        _add(x)
    if rec == "hold_and_clarify" and not out:
        _add("Keep the option open, but do not commit until the main blockers are clarified.")
    if missing and not any("rerun" in (x or "").lower() for x in out):
        _add("Once the missing information is filled, rerun the final decision.")
    if not out and rec == "not_recommended":
        _add("Do not prioritize this option unless new information materially improves the picture.")
    return _limit_items(out, 4)


def _build_user_facing_explanation(unified: dict) -> list:
    """生成 user_facing_explanation：面向用户的简短解释链。Phase5-A2。"""
    out = []
    rec = (unified.get("overall_recommendation") or "unknown").strip()
    h_sig = (unified.get("house_signal") or "unknown").strip()
    r_sig = (unified.get("risk_signal") or "unknown").strip()
    support = _safe_list(unified.get("support_trace") or unified.get("supporting_reasons") or [])
    blockers = _safe_list(unified.get("blocker_trace") or [])

    if rec == "proceed":
        out.append("The property still has enough strengths to remain under consideration.")
        out.append("The main risks appear manageable with normal checks.")
        out.append("That is why the current recommendation is to proceed.")
    elif rec == "proceed_with_caution":
        out.append("The property still has enough strengths to remain under consideration.")
        if blockers:
            out.append("However, a few important contract or information gaps make it wise to confirm details before committing.")
        else:
            out.append("However, a few points still need confirmation before you can move forward with confidence.")
        out.append("That is why the current recommendation is to proceed with caution.")
    elif rec == "hold_and_clarify":
        out.append("The property still has enough strengths to remain under consideration.")
        if h_sig == "unknown" or r_sig == "unknown":
            out.append("However, important information is still missing, so a full green light is not yet justified.")
        else:
            out.append("However, a few important contract or information gaps make it unsafe to give a full green light yet.")
        out.append("That is why the current recommendation is to hold and clarify rather than reject it outright.")
    elif rec == "not_recommended":
        out.append("The combined property and risk profile does not currently look strong enough.")
        out.append("The trade-offs and unresolved risks outweigh the positive factors.")
        out.append("That is why the current recommendation is not to proceed with this option.")
    else:
        out.append("The property and risk signals are still being assessed.")
        out.append("More information would help form a clearer recommendation.")
    return _limit_items(out, 4)


def _house_signal_from_final(house_final: dict) -> str:
    """从 house_final 提炼 house_signal。"""
    if not house_final or not isinstance(house_final, dict):
        return "unknown"
    conf = (house_final.get("decision_confidence") or "medium").strip().lower()
    primary = house_final.get("primary_recommendation") or {}
    watchouts = _safe_list(house_final.get("watchouts") or [])
    supporting = _safe_list(house_final.get("supporting_reasons") or [])
    summary = (house_final.get("final_summary") or "").strip().lower()

    if "not" in summary and "strong" in summary:
        return "weak"
    if "least compromised" in summary or "none of" in summary:
        return "weak"
    if conf == "low" and len(watchouts) >= 2:
        return "weak"
    if conf == "high" and len(supporting) >= 1 and len(watchouts) <= 1:
        return "positive"
    if len(watchouts) >= 2:
        return "mixed"
    if primary and (supporting or conf in ("high", "medium")):
        return "positive"
    return "mixed"


def _risk_signal_from_final(risk_final: dict) -> str:
    """从 risk_final 提炼 risk_signal。"""
    if not risk_final or not isinstance(risk_final, dict):
        return "unknown"
    safer = risk_final.get("safer_option") or {}
    higher = risk_final.get("higher_risk_option") or {}
    level = (safer.get("risk_level") or "").strip().lower()
    summary = (risk_final.get("final_summary") or "").strip().lower()
    watchouts = _safe_list(risk_final.get("watchouts") or [])

    if level == "high":
        if higher and higher.get("label"):
            return "high_risk"
        return "high_risk"
    if level == "low":
        return "manageable"
    if "too risky" in summary or "clarification" in summary and "before" in summary:
        return "high_risk"
    if "manageable" in summary or "still be manageable" in summary:
        return "caution"
    if len(watchouts) >= 2:
        return "caution"
    return "manageable"


def _overall_recommendation_from_signals(house_signal: str, risk_signal: str, house_final: dict, risk_final: dict) -> str:
    """根据 house_signal 和 risk_signal 判断 overall_recommendation。Phase4-A4: unknown != bad, missing != weak。"""
    has_house = bool(house_final and isinstance(house_final, dict))
    has_risk = bool(risk_final and isinstance(risk_final, dict))

    # 两侧都缺大量信息：不要武断 not_recommended，改为 hold_and_clarify
    if not has_house and not has_risk:
        return "hold_and_clarify"

    # house 强，但 risk 缺失：不要直接 proceed，改为 proceed_with_caution 或 hold_and_clarify
    if has_house and not has_risk:
        if house_signal == "weak":
            return "hold_and_clarify"
        return "hold_and_clarify"  # 风险未评估，保守处理

    # risk 有，但 house 缺失：不要直接 proceed
    if has_risk and not has_house:
        if risk_signal == "high_risk":
            return "hold_and_clarify"
        return "hold_and_clarify"  # 房源价值未评估

    # 两侧都有
    # not_recommended：只有信息足够且结论明确负面时
    if house_signal == "weak":
        return "not_recommended"
    if risk_signal == "high_risk":
        if house_signal in ("weak", "mixed"):
            return "not_recommended"
        return "hold_and_clarify"
    if house_signal == "weak" and risk_signal in ("caution", "high_risk"):
        return "not_recommended"

    if risk_signal == "high_risk":
        return "hold_and_clarify"
    if risk_signal == "caution" and house_signal in ("positive", "mixed"):
        return "hold_and_clarify"

    if risk_signal == "caution":
        return "proceed_with_caution"
    if house_signal == "mixed" and risk_signal == "manageable":
        return "proceed_with_caution"
    if house_signal == "positive" and risk_signal == "caution":
        return "proceed_with_caution"

    # proceed：只有两侧都有且信号一致时
    if house_signal == "positive" and risk_signal == "manageable":
        return "proceed"
    if house_signal == "mixed" and risk_signal == "manageable":
        return "proceed_with_caution"

    if house_signal == "unknown" or risk_signal == "unknown":
        return "hold_and_clarify"

    return "proceed_with_caution"


def build_unified_decision(
    house_final: dict | None = None,
    risk_final: dict | None = None,
) -> dict:
    """接收房源和风险最终结论，输出统一综合判断。Phase4-A2 / Phase4-A4。"""
    out = _empty_unified_decision()
    house_final = house_final if isinstance(house_final, dict) else None
    risk_final = risk_final if isinstance(risk_final, dict) else None

    # Phase4-A4: 缺失信息识别
    out["missing_information"] = []
    out["missing_information"].extend(_detect_missing_house_information(house_final))
    out["missing_information"].extend(_detect_missing_risk_information(risk_final))
    out["missing_information"] = _limit_items(out["missing_information"], 6)
    out["assessment_limitations"] = _build_assessment_limitations(house_final, risk_final)
    out["recommended_inputs_to_improve_decision"] = _build_recommended_inputs_to_improve_decision(house_final, risk_final)

    if not house_final and not risk_final:
        out["final_summary"] = "A reliable final decision is not yet available because important property-side and risk-side information is still missing."
        out["overall_recommendation"] = "hold_and_clarify"
        out["decision_confidence"] = "low"
        out["confidence_reason"] = "Confidence is low because both property and risk assessments are missing."
        out["final_action"] = "Clarify the missing data points first, then rerun the final decision."
        out["trace_summary"] = "The current decision is driven by missing information that still needs clarification."
        out["decision_trace"] = [
            "A reliable final decision is not yet available because important property-side and risk-side information is still missing.",
            "As a result, the current recommendation is to hold and clarify before moving forward.",
        ]
        out["user_facing_summary"] = "This option is not ready for a confident go-ahead yet. It would be better to clarify the key missing or risky points first."
        out["user_facing_reason"] = ["The current recommendation is not purely negative; it is mainly limited by unresolved details."]
        out["user_facing_risk_note"] = ["There may be missing information affecting how reliable the current recommendation is.", "The current result should be treated cautiously if the missing inputs are not filled."]
        out["user_facing_next_step"] = ["Clarify the missing data points first, then rerun the final decision."]
        out["user_facing_explanation"] = [
            "The property and risk signals are still being assessed.",
            "More information would help form a clearer recommendation.",
        ]
        return out

    house_signal = _house_signal_from_final(house_final) if house_final else "unknown"
    risk_signal = _risk_signal_from_final(risk_final) if risk_final else "unknown"
    out["house_signal"] = house_signal
    out["risk_signal"] = risk_signal

    out["overall_recommendation"] = _overall_recommendation_from_signals(
        house_signal, risk_signal, house_final or {}, risk_final or {}
    )

    # final_summary（Phase4-A4: 信息不完整时更诚实）
    if house_final and risk_final:
        if out["overall_recommendation"] == "proceed":
            out["final_summary"] = "The property still looks worth pursuing overall, and the current risk profile appears manageable with normal checks."
        elif out["overall_recommendation"] == "proceed_with_caution":
            out["final_summary"] = "This option remains possible, but both the property trade-offs and the unresolved risks suggest a cautious approach."
        elif out["overall_recommendation"] == "hold_and_clarify":
            out["final_summary"] = "The property itself looks promising, but the current contract or dispute risks should be clarified before moving forward."
        else:
            out["final_summary"] = "This option does not currently look strong enough to justify the level of risk and uncertainty involved."
    elif house_final:
        out["final_summary"] = "This property may still be worth considering, but the current contract or risk position has not been fully assessed yet."
    elif risk_final:
        out["final_summary"] = "The risk position may be manageable, but the overall property value and fit have not been fully evaluated yet."

    # decision_confidence（Phase4-A4: 考虑信息完整度）
    h_conf = (house_final.get("decision_confidence") or "medium").strip().lower() if house_final else "medium"
    r_conf = (risk_final.get("decision_confidence") or "medium").strip().lower() if risk_final else "medium"
    missing_count = len(out.get("missing_information") or [])
    if not house_final or not risk_final:
        out["decision_confidence"] = "low"
    elif house_signal == "unknown" or risk_signal == "unknown":
        out["decision_confidence"] = "low"
    elif missing_count >= 2:
        out["decision_confidence"] = "low"
    elif h_conf == "high" and r_conf == "high" and missing_count == 0:
        out["decision_confidence"] = "high"
    elif h_conf == "low" or r_conf == "low":
        out["decision_confidence"] = "low"
    else:
        out["decision_confidence"] = "medium"

    out["confidence_reason"] = _build_confidence_reason(out, house_final, risk_final)

    # decision_focus
    if out["overall_recommendation"] == "hold_and_clarify":
        out["decision_focus"] = "The main focus should be on clarifying the risk blockers before treating this as a viable option."
    elif out["overall_recommendation"] == "not_recommended":
        out["decision_focus"] = "The key decision is whether any new information could materially improve either the property case or the risk position."
    elif out["overall_recommendation"] == "proceed_with_caution":
        out["decision_focus"] = "The key decision is whether the property's strengths still justify moving forward once the unresolved contract risks are considered."
    else:
        out["decision_focus"] = "The key decision is whether the top-ranked option also matches your real non-negotiables in practice."

    # primary_blockers
    blockers = []
    if risk_final:
        blockers.extend(_safe_list(risk_final.get("watchouts") or [])[:2])
    if house_final:
        blockers.extend(_safe_list(house_final.get("watchouts") or [])[:2])
    out["primary_blockers"] = _limit_items(blockers, 4)

    # supporting_reasons
    supporting = []
    if house_final:
        supporting.extend(_safe_list(house_final.get("supporting_reasons") or [])[:2])
    if risk_final:
        supporting.extend(_safe_list(risk_final.get("supporting_reasons") or [])[:1])
    out["supporting_reasons"] = _limit_items(supporting, 3)

    # required_actions_before_proceeding
    actions = []
    if risk_final:
        fa = (risk_final.get("final_action") or "").strip()
        if fa:
            actions.append(fa)
        actions.extend(_safe_list(risk_final.get("watchouts") or [])[:2])
    if house_final and not actions:
        fa = (house_final.get("final_action") or "").strip()
        if fa:
            actions.append(fa)
    out["required_actions_before_proceeding"] = _limit_items(actions, 4)

    # final_action（Phase4-A4: 信息不完整时针对性动作）
    if not house_final and not risk_final:
        out["final_action"] = "Clarify the missing data points first, then rerun the final decision."
    elif not risk_final:
        out["final_action"] = "Complete the missing contract-risk review before treating this as a proceed decision."
    elif not house_final:
        out["final_action"] = "Fill the missing property evaluation inputs before making a final go/no-go call."
    elif out["overall_recommendation"] == "proceed":
        out["final_action"] = "Proceed with the viewing, but clarify the key contract terms in writing before committing."
    elif out["overall_recommendation"] == "proceed_with_caution":
        out["final_action"] = "Proceed with the viewing, but clarify the key contract terms in writing before committing."
    elif out["overall_recommendation"] == "hold_and_clarify":
        out["final_action"] = "Pause the process until the main risk blockers are clarified, then reassess whether the property still makes sense."
    else:
        out["final_action"] = "Do not prioritize this option further unless new information materially improves either the property case or the risk position."

    # house_reference
    if house_final:
        primary = house_final.get("primary_recommendation") or {}
        out["house_reference"] = {
            "primary_label": primary.get("label") or "",
            "confidence": house_final.get("decision_confidence") or "medium",
            "summary": (house_final.get("final_summary") or "")[:120] + ("..." if len(house_final.get("final_summary") or "") > 120 else ""),
        }
    else:
        out["house_reference"] = {}

    # risk_reference
    if risk_final:
        safer = risk_final.get("safer_option") or {}
        out["risk_reference"] = {
            "safer_label": safer.get("label") or "current_case",
            "confidence": risk_final.get("decision_confidence") or "medium",
            "summary": (risk_final.get("final_summary") or "")[:120] + ("..." if len(risk_final.get("final_summary") or "") > 120 else ""),
        }
    else:
        out["risk_reference"] = {}

    # Phase5-A1: Trace Layer
    out["house_trace_reasons"] = _extract_house_trace_reasons(house_final)
    out["risk_trace_reasons"] = _extract_risk_trace_reasons(risk_final)
    out["blocker_trace"] = _build_blocker_trace(out, house_final, risk_final)
    out["support_trace"] = _build_support_trace(out, house_final, risk_final)
    out["decision_trace"] = _build_decision_trace(out, house_final, risk_final)
    out["trace_summary"] = _build_trace_summary(out)

    # Phase5-A2: Explain-to-User Layer
    out["user_facing_summary"] = _build_user_facing_summary(out)
    out["user_facing_reason"] = _build_user_facing_reason(out)
    out["user_facing_risk_note"] = _build_user_facing_risk_note(out)
    out["user_facing_next_step"] = _build_user_facing_next_step(out)
    out["user_facing_explanation"] = _build_user_facing_explanation(out)

    return out


def format_unified_decision_for_cli(data: dict | None, max_items: int = 2) -> str:
    """将 Unified Decision 转为 CLI 文本。Phase4-A2 / Phase4-A4 / Phase5-A1 / Phase5-A2 / Phase5-A3。"""
    payload = export_unified_decision_payload(data)
    if not payload:
        return ""
    status = payload.get("status") or {}
    decision = payload.get("decision") or {}
    analysis = payload.get("analysis") or {}
    trace = payload.get("trace") or {}
    user_facing = payload.get("user_facing") or {}
    parts = []

    rec = (status.get("overall_recommendation") or "unknown").strip()
    parts.append("Overall Recommendation: %s" % rec)

    user_sum = (user_facing.get("summary") or "").strip()
    if user_sum:
        parts.append("User Summary: %s" % user_sum)

    why = _limit_items(user_facing.get("reason") or [], 2)
    if why:
        parts.append(_join_cli_section("Why This Recommendation", why))

    watch = _limit_items(user_facing.get("risk_note") or [], 2)
    if watch:
        parts.append(_join_cli_section("What To Watch", watch))

    next_steps = _limit_items(user_facing.get("next_step") or [], 2)
    if next_steps:
        parts.append(_join_cli_section("Next Step", next_steps))

    action = (decision.get("final_action") or "").strip()
    if action:
        parts.append("Final Action: %s" % action)

    summary = (decision.get("final_summary") or "").strip()
    if summary:
        parts.append("Final Summary: %s" % summary)

    trace_sum = (trace.get("trace_summary") or "").strip()
    if trace_sum:
        parts.append("Trace Summary: %s" % trace_sum)

    conf = (status.get("decision_confidence") or "medium").strip()
    parts.append("Confidence: %s" % conf)

    conf_reason = (status.get("confidence_reason") or "").strip()
    if conf_reason:
        parts.append("Confidence Reason: %s" % conf_reason)

    h_sig = (decision.get("house_signal") or "unknown").strip()
    r_sig = (decision.get("risk_signal") or "unknown").strip()
    parts.append("House Signal: %s | Risk Signal: %s" % (h_sig, r_sig))

    focus = (decision.get("decision_focus") or "").strip()
    if focus:
        parts.append("Decision Focus: %s" % focus)

    decision_trace = _limit_items(trace.get("decision_trace") or [], 3)
    if decision_trace:
        parts.append(_join_cli_section("Decision Trace", decision_trace))

    blocker_trace = _limit_items(trace.get("blocker_trace") or [], 2)
    if blocker_trace:
        parts.append(_join_cli_section("Blocker Trace", blocker_trace))

    support_trace = _limit_items(trace.get("support_trace") or [], 2)
    if support_trace:
        parts.append(_join_cli_section("Support Trace", support_trace))

    missing = _limit_items(analysis.get("missing_information") or [], 3)
    if missing:
        parts.append(_join_cli_section("Missing Information", missing))

    limitations = _limit_items(analysis.get("assessment_limitations") or [], 2)
    if limitations:
        parts.append(_join_cli_section("Assessment Limitations", limitations))

    supporting = _limit_items(analysis.get("supporting_reasons") or [], max_items)
    if supporting:
        parts.append(_join_cli_section("Supporting Reasons", supporting))

    blockers = _limit_items(analysis.get("primary_blockers") or [], max_items)
    if blockers:
        parts.append(_join_cli_section("Primary Blockers", blockers))

    actions = _limit_items(analysis.get("required_actions_before_proceeding") or [], max_items)
    if actions:
        parts.append(_join_cli_section("Required Actions Before Proceeding", actions))

    recommended = _limit_items(analysis.get("recommended_inputs_to_improve_decision") or [], 3)
    if recommended:
        parts.append(_join_cli_section("Recommended Inputs To Improve Decision", recommended))

    if action and not any("Final Action:" in p for p in parts):
        parts.append("Final Action: %s" % action)

    return "\n\n".join(parts) if parts else ""


# ---------- Phase5-A3: 输出协议层 Output Contract ----------

def normalize_unified_decision(unified: dict | None) -> dict:
    """把 unified_decision 补齐缺失字段，安全标准化。Phase5-A3。"""
    if unified is None or not isinstance(unified, dict):
        return _empty_unified_decision()
    out = _empty_unified_decision()
    for k in out:
        v = unified.get(k)
        if v is None:
            continue
        if isinstance(out[k], list):
            out[k] = _safe_list(v)
        elif isinstance(out[k], str):
            out[k] = str(v).strip() if v else ""
        elif isinstance(out[k], dict):
            out[k] = v if isinstance(v, dict) else {}
    return out


def export_unified_decision_payload(unified: dict | None) -> dict:
    """输出完整协议层 payload。Phase5-A3。"""
    n = normalize_unified_decision(unified)
    rec = (n.get("overall_recommendation") or "").strip()
    if rec in ("", "unknown"):
        rec = "hold_and_clarify"
    conf = (n.get("decision_confidence") or "low").strip()
    return {
        "status": {
            "overall_recommendation": rec,
            "decision_confidence": conf,
            "confidence_reason": (n.get("confidence_reason") or "").strip(),
        },
        "decision": {
            "final_summary": (n.get("final_summary") or "").strip(),
            "decision_focus": (n.get("decision_focus") or "").strip(),
            "final_action": (n.get("final_action") or "").strip(),
            "house_signal": (n.get("house_signal") or "unknown").strip(),
            "risk_signal": (n.get("risk_signal") or "unknown").strip(),
        },
        "analysis": {
            "supporting_reasons": _safe_list(n.get("supporting_reasons") or []),
            "primary_blockers": _safe_list(n.get("primary_blockers") or []),
            "required_actions_before_proceeding": _safe_list(n.get("required_actions_before_proceeding") or []),
            "missing_information": _safe_list(n.get("missing_information") or []),
            "assessment_limitations": _safe_list(n.get("assessment_limitations") or []),
            "recommended_inputs_to_improve_decision": _safe_list(n.get("recommended_inputs_to_improve_decision") or []),
        },
        "trace": {
            "trace_summary": (n.get("trace_summary") or "").strip(),
            "decision_trace": _safe_list(n.get("decision_trace") or []),
            "house_trace_reasons": _safe_list(n.get("house_trace_reasons") or []),
            "risk_trace_reasons": _safe_list(n.get("risk_trace_reasons") or []),
            "blocker_trace": _safe_list(n.get("blocker_trace") or []),
            "support_trace": _safe_list(n.get("support_trace") or []),
        },
        "user_facing": {
            "summary": (n.get("user_facing_summary") or "").strip(),
            "reason": _safe_list(n.get("user_facing_reason") or []),
            "risk_note": _safe_list(n.get("user_facing_risk_note") or []),
            "next_step": _safe_list(n.get("user_facing_next_step") or []),
            "explanation": _safe_list(n.get("user_facing_explanation") or []),
        },
        "references": {
            "house_reference": n.get("house_reference") if isinstance(n.get("house_reference"), dict) else {},
            "risk_reference": n.get("risk_reference") if isinstance(n.get("risk_reference"), dict) else {},
        },
    }


def format_unified_decision_for_api(unified: dict | None) -> dict:
    """返回适合 API/前端直接读取的 payload。Phase5-A3。"""
    return export_unified_decision_payload(unified)


def format_unified_decision_for_agent(unified: dict | None) -> dict:
    """返回适合 Agent / Planner 使用的精简结构。Phase5-A3。"""
    payload = export_unified_decision_payload(unified)
    status = payload.get("status") or {}
    decision = payload.get("decision") or {}
    analysis = payload.get("analysis") or {}
    trace = payload.get("trace") or {}
    user_facing = payload.get("user_facing") or {}
    refs = payload.get("references") or {}

    blockers = list(analysis.get("primary_blockers") or [])
    for x in (trace.get("blocker_trace") or []):
        if x and x not in blockers:
            blockers.append(x)

    supports = list(analysis.get("supporting_reasons") or [])
    for x in (trace.get("support_trace") or []):
        if x and x not in supports:
            supports.append(x)

    return {
        "decision_signal": (status.get("overall_recommendation") or "hold_and_clarify").strip(),
        "confidence": (status.get("decision_confidence") or "low").strip(),
        "focus": (decision.get("decision_focus") or "").strip(),
        "summary": (decision.get("final_summary") or "").strip(),
        "blockers": blockers[:4],
        "supports": supports[:4],
        "required_actions": _safe_list(analysis.get("required_actions_before_proceeding") or [])[:4],
        "missing_information": _safe_list(analysis.get("missing_information") or [])[:4],
        "user_message": (user_facing.get("summary") or "").strip(),
        "references": {
            "house": refs.get("house_reference") or {},
            "risk": refs.get("risk_reference") or {},
        },
    }


# ---------- Phase5-A4: 模块自检 ----------

def run_explain_engine_self_check() -> dict:
    """快速检查 Module7 关键能力是否都存在。Phase5-A4。"""
    out = {
        "house_explanation": False,
        "risk_explanation": False,
        "snapshot": False,
        "house_final": False,
        "risk_final": False,
        "unified_decision": False,
        "payload_export": False,
        "cli_format": False,
        "api_format": False,
        "agent_format": False,
        "all_passed": False,
    }
    h = r = s = house_final = risk_final = ud = None
    try:
        h = explain_house({"price_score": 80, "commute_score": 70, "area_score": 60})
        out["house_explanation"] = bool(h and isinstance(h, dict) and "summary" in h)
    except Exception:
        pass
    try:
        r = build_risk_explanation({"overall_risk_level": "low", "risk_score": 2})
        out["risk_explanation"] = bool(r and isinstance(r, dict) and "summary" in r)
    except Exception:
        pass
    try:
        s = build_explanation_snapshot(h or explain_house({"price_score": 80}))
        out["snapshot"] = bool(s and isinstance(s, dict))
    except Exception:
        pass
    try:
        house_final = build_final_house_recommendation(
            [{"final_score": 82, "explanation_summary": {}}], labels=["R1"], top_n=1
        )
        out["house_final"] = bool(house_final and house_final.get("primary_recommendation"))
    except Exception:
        pass
    try:
        risk_final = build_final_risk_recommendation({"overall_risk_level": "low", "risk_score": 2}, label="C")
        out["risk_final"] = bool(risk_final and risk_final.get("safer_option"))
    except Exception:
        pass
    try:
        ud = build_unified_decision(house_final, risk_final)
        out["unified_decision"] = bool(ud and isinstance(ud, dict) and "overall_recommendation" in ud)
    except Exception:
        pass
    try:
        payload = export_unified_decision_payload(ud or {})
        out["payload_export"] = bool(payload and "status" in payload and "user_facing" in payload)
    except Exception:
        pass
    try:
        cli = format_unified_decision_for_cli(ud or {})
        out["cli_format"] = isinstance(cli, str) and len(cli) >= 10
    except Exception:
        pass
    try:
        api = format_unified_decision_for_api(ud or {})
        out["api_format"] = bool(api and isinstance(api, dict) and "status" in api)
    except Exception:
        pass
    try:
        agent = format_unified_decision_for_agent(ud or {})
        out["agent_format"] = bool(agent and isinstance(agent, dict) and "decision_signal" in agent)
    except Exception:
        pass
    out["all_passed"] = all(
        out[k] for k in [
            "house_explanation", "risk_explanation", "snapshot", "house_final", "risk_final",
            "unified_decision", "payload_export", "cli_format", "api_format", "agent_format"
        ]
    )
    return out


def attach_unified_decision(
    result: dict,
    house_key: str = "final_recommendation",
    risk_key: str = "final_risk_recommendation",
    unified_key: str = "unified_decision",
    payload_key: str = "unified_decision_payload",
) -> dict:
    """从 result 中读取 house/risk final recommendation，生成 unified_decision 并挂载。Phase4-A3 / Phase5-A3。"""
    if not result or not isinstance(result, dict):
        return result
    house_final = result.get(house_key) if house_key else None
    risk_final = result.get(risk_key) if risk_key else None
    if not house_final and not risk_final:
        result[unified_key] = build_unified_decision(None, None)
    else:
        try:
            result[unified_key] = build_unified_decision(house_final, risk_final)
        except Exception:
            result[unified_key] = _empty_unified_decision()
    result[payload_key] = export_unified_decision_payload(result.get(unified_key))
    return result


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

    # Phase3-A4: 最终推荐结论示例
    print("\n=== Phase3-A4: build_final_house_recommendation ===")
    final_rec = build_final_house_recommendation(top3, labels=["Rank 1", "Rank 2", "Rank 3"], top_n=3)
    print("final_summary:", final_rec.get("final_summary"))
    print("primary:", final_rec.get("primary_recommendation"))
    print("backup:", final_rec.get("backup_recommendation"))
    print("confidence:", final_rec.get("decision_confidence"))
    print("\n--- format_final_recommendation_for_cli ---")
    print(format_final_recommendation_for_cli(final_rec))

    # Phase4-A1: Risk Final Recommendation 示例
    print("\n=== Phase4-A1: build_final_risk_recommendation (single) ===")
    single_risk = {"overall_risk_level": "high", "risk_score": 8}
    single_risk["explanation_summary"] = build_explanation_snapshot(build_risk_explanation(single_risk))
    final_single = build_final_risk_recommendation(single_risk, label="Current Case")
    print("final_summary:", final_single.get("final_summary"))
    print("safer_option:", final_single.get("safer_option"))
    print("\n--- format_final_risk_recommendation_for_cli (single) ---")
    print(format_final_risk_recommendation_for_cli(final_single))

    print("\n=== Phase4-A1: build_final_risk_comparison_recommendation (two risks) ===")
    risk_a = {"overall_risk_level": "high", "risk_score": 8}
    risk_b = {"overall_risk_level": "medium", "structured_risk_score": 4}
    risk_a["explanation_summary"] = build_explanation_snapshot(build_risk_explanation(risk_a))
    risk_b["explanation_summary"] = build_explanation_snapshot(build_risk_explanation(risk_b))
    final_comp = build_final_risk_comparison_recommendation([risk_a, risk_b], labels=["Contract A", "Contract B"])
    print("final_summary:", final_comp.get("final_summary"))
    print("safer_option:", final_comp.get("safer_option"))
    print("higher_risk_option:", final_comp.get("higher_risk_option"))
    print("\n--- format_final_risk_recommendation_for_cli (comparison) ---")
    print(format_final_risk_recommendation_for_cli(final_comp))

    # Phase4-A2: Unified Decision 示例
    print("\n=== Phase4-A2: build_unified_decision ===")
    # 场景1: proceed (house 强 + risk 低)
    house_strong = build_final_house_recommendation(top3, labels=["Rank 1", "Rank 2", "Rank 3"], top_n=3)
    risk_low = build_final_risk_recommendation({"overall_risk_level": "low", "risk_score": 2}, label="Current Case")
    ud1 = build_unified_decision(house_strong, risk_low)
    print("--- Scenario: proceed (house strong + risk low) ---")
    print("overall_recommendation:", ud1.get("overall_recommendation"))
    print(format_unified_decision_for_cli(ud1))

    # 场景2: hold_and_clarify (house 强 + risk 高)
    risk_high = build_final_risk_recommendation(single_risk, label="Current Case")
    ud2 = build_unified_decision(house_strong, risk_high)
    print("\n--- Scenario: hold_and_clarify (house strong + risk high) ---")
    print("overall_recommendation:", ud2.get("overall_recommendation"))

    # 场景3: proceed_with_caution (house mixed + risk caution)
    house_mixed = build_final_house_recommendation([house_b], labels=["Option 1"], top_n=1)
    risk_caution = build_final_risk_recommendation({"overall_risk_level": "medium", "risk_score": 5}, label="Current Case")
    ud2b = build_unified_decision(house_mixed, risk_caution)
    print("\n--- Scenario: proceed_with_caution (house mixed + risk caution) ---")
    print("overall_recommendation:", ud2b.get("overall_recommendation"))

    # 场景4: not_recommended (house 弱 + risk 高)
    house_very_weak = {"final_score": 42, "price_score": 40, "commute_score": 45, "area_score": 35}
    house_very_weak["explanation_summary"] = {"recommendation": "no", "key_risks": ["Weak overall fit.", "High trade-offs."], "key_positives": []}
    house_weak = build_final_house_recommendation([house_very_weak], labels=["Option 1"], top_n=1)
    ud3 = build_unified_decision(house_weak, risk_high)
    print("\n--- Scenario: not_recommended (house weak + risk high) ---")
    print("overall_recommendation:", ud3.get("overall_recommendation"))

    # Phase4-A3: attach_unified_decision 主流程演示
    print("\n=== Phase4-A3: attach_unified_decision (主流程演示) ===")
    result = {"final_recommendation": house_strong, "final_risk_recommendation": risk_low}
    attach_unified_decision(result)
    print("unified_decision keys:", list(result.get("unified_decision", {}).keys()))
    print("overall_recommendation:", result.get("unified_decision", {}).get("overall_recommendation"))
    print("\n--- format_unified_decision_for_cli (house+risk) ---")
    print(format_unified_decision_for_cli(result.get("unified_decision", {})))

    # Phase4-A4: 缺失信息场景演示（unknown != bad）
    print("\n=== Phase4-A4: 缺失信息场景 (unknown != bad) ===")
    # 场景1: house 有，risk 缺失
    ud_house_only = build_unified_decision(house_strong, None)
    print("--- 1) House only, risk missing ---")
    print("overall_recommendation:", ud_house_only.get("overall_recommendation"))
    print("missing_information:", ud_house_only.get("missing_information"))
    print("final_summary:", (ud_house_only.get("final_summary") or "")[:80] + "...")

    # 场景2: risk 有，house 缺失
    ud_risk_only = build_unified_decision(None, risk_low)
    print("\n--- 2) Risk only, house missing ---")
    print("overall_recommendation:", ud_risk_only.get("overall_recommendation"))
    print("missing_information:", ud_risk_only.get("missing_information"))

    # 场景3: 两边都不完整
    ud_both_missing = build_unified_decision(None, None)
    print("\n--- 3) Both missing ---")
    print("overall_recommendation:", ud_both_missing.get("overall_recommendation"))
    print("final_summary:", ud_both_missing.get("final_summary"))
    print("\n--- format_unified_decision_for_cli (both missing) ---")
    print(format_unified_decision_for_cli(ud_both_missing))

    # Phase5-A1: Trace Layer 演示
    print("\n=== Phase5-A1: Trace Layer (可追溯原因链) ===")
    # 场景1: proceed_with_caution
    ud_trace1 = build_unified_decision(house_mixed, risk_caution)
    print("--- Scenario: proceed_with_caution ---")
    print("overall_recommendation:", ud_trace1.get("overall_recommendation"))
    print("trace_summary:", ud_trace1.get("trace_summary"))
    print("house_trace_reasons:", ud_trace1.get("house_trace_reasons"))
    print("risk_trace_reasons:", ud_trace1.get("risk_trace_reasons"))
    print("blocker_trace:", ud_trace1.get("blocker_trace"))
    print("support_trace:", ud_trace1.get("support_trace"))
    print("decision_trace:", ud_trace1.get("decision_trace"))
    print("\n--- format_unified_decision_for_cli (proceed_with_caution) ---")
    print(format_unified_decision_for_cli(ud_trace1))

    # 场景2: hold_and_clarify
    ud_trace2 = build_unified_decision(house_strong, risk_high)
    print("\n--- Scenario: hold_and_clarify ---")
    print("overall_recommendation:", ud_trace2.get("overall_recommendation"))
    print("trace_summary:", ud_trace2.get("trace_summary"))
    print("decision_trace:", ud_trace2.get("decision_trace"))
    print("\n--- format_unified_decision_for_cli (hold_and_clarify) ---")
    print(format_unified_decision_for_cli(ud_trace2))

    # Phase5-A2: Explain-to-User Layer 演示
    print("\n=== Phase5-A2: Explain-to-User Layer (用户可解释输出) ===")
    # 场景1: proceed
    print("--- 1) proceed ---")
    print("user_facing_summary:", ud1.get("user_facing_summary"))
    print("user_facing_reason:", ud1.get("user_facing_reason"))
    print("user_facing_next_step:", ud1.get("user_facing_next_step"))
    print("\n--- format (proceed) ---")
    print(format_unified_decision_for_cli(ud1))

    # 场景2: proceed_with_caution (house mixed + risk medium)
    ud_caution = build_unified_decision(house_mixed, risk_caution)
    print("\n--- 2) proceed_with_caution / hold_and_clarify ---")
    print("overall_recommendation:", ud_caution.get("overall_recommendation"))
    print("user_facing_summary:", ud_caution.get("user_facing_summary"))
    print("user_facing_reason:", ud_caution.get("user_facing_reason"))
    print("user_facing_risk_note:", ud_caution.get("user_facing_risk_note"))

    # 场景3: hold_and_clarify / not_recommended
    print("\n--- 3) hold_and_clarify ---")
    print("user_facing_summary:", ud_trace2.get("user_facing_summary"))
    print("user_facing_explanation:", ud_trace2.get("user_facing_explanation"))
    print("\n--- 4) not_recommended ---")
    print("user_facing_summary:", ud3.get("user_facing_summary"))
    print("user_facing_next_step:", ud3.get("user_facing_next_step"))

    # Phase5-A3: 输出协议层演示
    print("\n=== Phase5-A3: 输出协议层 (Output Contract) ===")
    # 场景1: proceed_with_caution / hold_and_clarify
    ud_caution = build_unified_decision(house_mixed, risk_caution)
    payload = export_unified_decision_payload(ud_caution)
    print("--- 1) export_unified_decision_payload (hold_and_clarify) ---")
    print("payload keys:", list(payload.keys()))
    print("status:", payload.get("status"))
    print("user_facing.summary:", payload.get("user_facing", {}).get("summary"))

    api_out = format_unified_decision_for_api(ud_caution)
    print("\n--- format_unified_decision_for_api ---")
    print("api keys:", list(api_out.keys()))

    agent_out = format_unified_decision_for_agent(ud_caution)
    print("\n--- format_unified_decision_for_agent ---")
    print("decision_signal:", agent_out.get("decision_signal"))
    print("confidence:", agent_out.get("confidence"))
    print("blockers:", agent_out.get("blockers"))
    print("user_message:", (agent_out.get("user_message") or "")[:60] + "...")

    # 场景2: hold_and_clarify
    payload2 = export_unified_decision_payload(ud_trace2)
    print("\n--- 2) hold_and_clarify payload ---")
    print("status.overall_recommendation:", payload2.get("status", {}).get("overall_recommendation"))
    print("trace.decision_trace (first):", (payload2.get("trace", {}).get("decision_trace") or [])[:1])

    # attach 后 result 含 unified_decision_payload
    print("\n--- attach_unified_decision 含 payload ---")
    print("unified_decision_payload keys:", list(result.get("unified_decision_payload", {}).keys()))

    # Phase5-A4: Module7 收口验收演示
    print("\n=== Phase5-A4: Module7 收口验收 (Explain Engine Self-Check) ===")
    check = run_explain_engine_self_check()
    for k, v in check.items():
        print("  %s: %s" % (k, v))
    print("Module7 验收结果: %s" % ("PASS" if check.get("all_passed") else "FAIL"))
