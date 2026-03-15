# Module3 Phase4-4：重点条款摘要（Highlighted Clauses）
# 从 risk_clauses 中筛选最值得用户优先查看的重点条款，生成 highlighted_clauses，为文档风险摘要输出做准备。

# risk_flag -> highlight_reason 简短说明（与 risk_clause_detector 的 flag 一致）
FLAG_TO_HIGHLIGHT_REASON = {
    "deposit_risk": "该条款直接涉及押金处理，建议优先核查。",
    "rent_increase_risk": "该条款涉及涨租条件，可能影响后续租金安排。",
    "notice_risk": "该条款涉及解约或通知规则，建议重点确认。",
    "eviction_risk": "该条款涉及收回房屋或驱逐程序，建议重点确认。",
    "repair_risk": "该条款涉及维修责任划分，容易引发后续争议。",
    "fee_charge_risk": "该条款涉及收费或额外费用，建议重点核对。",
    "unfair_clause": "该条款可能偏向单方，存在公平性风险。",
}

# risk_level 排序权重：高优先
RISK_LEVEL_ORDER = {"high": 3, "medium": 2, "low": 1}


def _highlight_reason_for_flags(risk_flags: list) -> str:
    """根据 risk_flags 生成一句 highlight_reason；多 flag 时合并为简短一句。"""
    if not risk_flags:
        return "该条款存在风险点，建议重点查看。"
    reasons = []
    for f in risk_flags:
        r = FLAG_TO_HIGHLIGHT_REASON.get(f)
        if r and r not in reasons:
            reasons.append(r)
    if not reasons:
        return "该条款存在风险点，建议重点查看。"
    if len(reasons) == 1:
        return reasons[0]
    # 合并为一句，避免过长：取首条 + 「另涉及…」
    return reasons[0] + " 另涉及相关风险，建议一并确认。"


def build_highlighted_clauses(risk_clauses: list[dict], max_items: int = 3) -> list[dict]:
    """
    从 risk_clauses 中按风险程度筛选出重点条款，最多返回 max_items 条。
    规则：优先 risk_level 高（high > medium > low），同等级则优先 risk_flags 数量多，再按原顺序。
    每条在原有字段基础上增加 highlight_reason。
    """
    if not risk_clauses or not isinstance(risk_clauses, list):
        return []
    # 排序：level 降序，再按 risk_flags 数量降序，否则保持原序
    def sort_key(item):
        level = (item.get("risk_level") or "low").strip().lower()
        level_score = RISK_LEVEL_ORDER.get(level, 0)
        flag_count = len(item.get("risk_flags") or [])
        return (-level_score, -flag_count)

    sorted_clauses = sorted(risk_clauses, key=sort_key)
    selected = sorted_clauses[:max_items]
    out = []
    for rc in selected:
        if not isinstance(rc, dict):
            continue
        out.append({
            "block_id": rc.get("block_id", ""),
            "page": rc.get("page"),
            "section_title": rc.get("section_title") or "",
            "text": rc.get("text", ""),
            "risk_flags": list(rc.get("risk_flags") or []),
            "risk_level": rc.get("risk_level") or "low",
            "highlight_reason": _highlight_reason_for_flags(rc.get("risk_flags") or []),
        })
    return out
