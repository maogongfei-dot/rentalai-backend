from typing import Any, Dict, List, Optional


def build_explanation_result(analysis_result: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    输入：
        analysis_result: 任意已有分析结果字典
        优先尝试从中提取：
        - score
        - risks
        - reasons

    输出：
        {
            "summary": str,
            "pros": list[str],
            "cons": list[str],
            "recommendation": str
        }
    """
    analysis_result = analysis_result or {}

    score = _extract_score(analysis_result)
    risks = _extract_risks(analysis_result)
    reasons = _extract_reasons(analysis_result)

    normalized_score = _normalize_score(score)
    normalized_risks = _normalize_risks(risks)
    normalized_reasons = _normalize_reasons(reasons)

    pros = _build_pros(normalized_score, normalized_risks, normalized_reasons)
    cons = _build_cons(normalized_score, normalized_risks, normalized_reasons)
    summary = _build_summary(normalized_score, pros, cons, normalized_risks)
    recommendation = _build_recommendation(normalized_score, normalized_risks)

    return {
        "summary": summary,
        "pros": pros,
        "cons": cons,
        "recommendation": recommendation,
    }


def _extract_score(data: Dict[str, Any]) -> Any:
    candidate_keys = [
        "score",
        "final_score",
        "total_score",
        "overall_score",
    ]

    for key in candidate_keys:
        if key in data:
            return data.get(key)

    nested_dict_keys = [
        "result",
        "analysis",
        "analysis_result",
        "scores",
        "scoring",
    ]

    nested_score_keys = [
        "score",
        "final_score",
        "total_score",
        "overall_score",
    ]

    for parent_key in nested_dict_keys:
        parent_value = data.get(parent_key)
        if isinstance(parent_value, dict):
            for child_key in nested_score_keys:
                if child_key in parent_value:
                    return parent_value.get(child_key)

    return None


def _extract_risks(data: Dict[str, Any]) -> List[Any]:
    candidate_keys = [
        "risks",
        "risk_items",
        "risk_list",
        "issues",
        "problems",
    ]

    for key in candidate_keys:
        value = data.get(key)
        if isinstance(value, list):
            return value

    nested_dict_keys = [
        "result",
        "analysis",
        "analysis_result",
        "risk_result",
        "contract_result",
    ]

    nested_risk_keys = [
        "risks",
        "risk_items",
        "risk_list",
        "issues",
        "problems",
    ]

    for parent_key in nested_dict_keys:
        parent_value = data.get(parent_key)
        if isinstance(parent_value, dict):
            for child_key in nested_risk_keys:
                child_value = parent_value.get(child_key)
                if isinstance(child_value, list):
                    return child_value

    return []


def _extract_reasons(data: Dict[str, Any]) -> List[Any]:
    candidate_keys = [
        "reasons",
        "reason_list",
        "highlights",
        "pros",
        "good_points",
    ]

    for key in candidate_keys:
        value = data.get(key)
        if isinstance(value, list):
            return value

    nested_dict_keys = [
        "result",
        "analysis",
        "analysis_result",
        "explanation",
        "summary_result",
    ]

    nested_reason_keys = [
        "reasons",
        "reason_list",
        "highlights",
        "pros",
        "good_points",
    ]

    for parent_key in nested_dict_keys:
        parent_value = data.get(parent_key)
        if isinstance(parent_value, dict):
            for child_key in nested_reason_keys:
                child_value = parent_value.get(child_key)
                if isinstance(child_value, list):
                    return child_value

    return []


def _normalize_score(score: Any) -> Optional[float]:
    if score is None:
        return None

    try:
        return float(score)
    except (TypeError, ValueError):
        return None


def _normalize_risks(risks: List[Any]) -> List[Dict[str, str]]:
    normalized = []

    for item in risks:
        if isinstance(item, dict):
            title = str(item.get("title") or item.get("name") or item.get("risk") or item.get("issue") or "Unknown risk").strip()
            level = str(item.get("level") or item.get("severity") or item.get("risk_level") or "medium").strip().lower()
            detail = str(item.get("detail") or item.get("description") or item.get("reason") or "").strip()
        else:
            title = str(item).strip()
            level = "medium"
            detail = ""

        if level not in {"low", "medium", "high"}:
            level = "medium"

        if title:
            normalized.append(
                {
                    "title": title,
                    "level": level,
                    "detail": detail,
                }
            )

    return normalized


def _normalize_reasons(reasons: List[Any]) -> List[str]:
    cleaned = []

    for item in reasons:
        if isinstance(item, dict):
            text = str(
                item.get("text")
                or item.get("reason")
                or item.get("title")
                or item.get("label")
                or ""
            ).strip()
        else:
            text = str(item).strip()

        if text:
            cleaned.append(text)

    return cleaned


def _build_pros(
    score: Optional[float],
    risks: List[Dict[str, str]],
    reasons: List[str],
) -> List[str]:
    pros: List[str] = []

    if score is not None:
        if score >= 80:
            pros.append("整体评分较高，说明当前结果总体偏稳妥。")
        elif score >= 60:
            pros.append("整体评分中上，说明存在可接受基础。")

    high_risk_count = sum(1 for risk in risks if risk["level"] == "high")
    medium_risk_count = sum(1 for risk in risks if risk["level"] == "medium")

    if high_risk_count == 0:
        pros.append("当前结果中没有发现高风险项。")

    if high_risk_count == 0 and medium_risk_count <= 1:
        pros.append("主要风险数量不多，处理难度相对可控。")

    for reason in reasons[:3]:
        pros.append(f"有利因素：{reason}")

    return _deduplicate_items(pros)[:5]


def _build_cons(
    score: Optional[float],
    risks: List[Dict[str, str]],
    reasons: List[str],
) -> List[str]:
    cons: List[str] = []

    if score is not None:
        if score < 40:
            cons.append("整体评分偏低，说明当前结果存在明显问题。")
        elif score < 60:
            cons.append("整体评分一般，说明仍有一些关键问题需要注意。")

    sorted_risks = sorted(risks, key=_risk_sort_key, reverse=True)

    for risk in sorted_risks[:3]:
        if risk["detail"]:
            cons.append(f"风险项：{risk['title']}（{_risk_level_cn(risk['level'])}）- {risk['detail']}")
        else:
            cons.append(f"风险项：{risk['title']}（{_risk_level_cn(risk['level'])}）")

    if not cons and not reasons and not risks:
        cons.append("当前输入信息较少，暂时无法输出更细的风险解释。")

    return _deduplicate_items(cons)[:5]


def _build_summary(
    score: Optional[float],
    pros: List[str],
    cons: List[str],
    risks: List[Dict[str, str]],
) -> str:
    if score is None:
        score_text = "当前结果暂无明确评分"
    else:
        score_text = f"当前结果评分为 {int(score) if score.is_integer() else round(score, 1)} 分"

    high_risk_count = sum(1 for risk in risks if risk["level"] == "high")
    medium_risk_count = sum(1 for risk in risks if risk["level"] == "medium")

    if high_risk_count >= 2:
        risk_text = "且高风险项较多，整体不够稳妥。"
    elif high_risk_count == 1:
        risk_text = "且存在 1 个高风险项，需要优先处理。"
    elif medium_risk_count >= 2:
        risk_text = "且中风险项较多，建议继续核查。"
    else:
        risk_text = "整体风险相对可控。"

    if pros and not cons:
        tail_text = "从现有结果看，整体偏正面。"
    elif cons and not pros:
        tail_text = "从现有结果看，整体偏谨慎。"
    else:
        tail_text = "从现有结果看，优缺点并存。"

    return f"{score_text}，{risk_text}{tail_text}"


def _build_recommendation(score: Optional[float], risks: List[Dict[str, str]]) -> str:
    high_risk_count = sum(1 for risk in risks if risk["level"] == "high")
    medium_risk_count = sum(1 for risk in risks if risk["level"] == "medium")

    if high_risk_count >= 2:
        return "不建议直接继续，除非高风险项已经逐条解决。"

    if high_risk_count == 1:
        return "建议先处理高风险项，再决定是否继续。"

    if score is None:
        return "建议补充更多信息后再做判断。"

    if score >= 80 and medium_risk_count == 0:
        return "总体建议可以继续推进。"

    if score >= 60:
        return "总体可以继续，但建议带着问题清单继续核查。"

    return "目前更建议谨慎处理，先补强薄弱部分再继续。"


def _risk_sort_key(risk: Dict[str, str]) -> int:
    level = risk.get("level", "medium")
    if level == "high":
        return 3
    if level == "medium":
        return 2
    return 1


def _risk_level_cn(level: str) -> str:
    if level == "high":
        return "高风险"
    if level == "low":
        return "低风险"
    return "中风险"


def _deduplicate_items(items: List[str]) -> List[str]:
    seen = set()
    result = []

    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)

    return result
