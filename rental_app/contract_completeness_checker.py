# Module3 Phase5-3：合同完整性检查（Contract Completeness Check）
# 根据 missing_clauses 与 weak_clauses 输出完整性等级与摘要，便于判断合同整体是否完整、需优先补强的部分。

# 等级对应摘要（简洁自然语言）
COMPLETENESS_SUMMARY_MAP = {
    "low": "合同缺失较多关键条款，完整性偏低，建议优先补充。",
    "medium": "合同存在部分缺失或较弱条款，完整性一般，建议进一步完善。",
    "high": "合同主要条款较完整，仅存在少量可优化内容。",
}


def build_contract_completeness(
    missing_clauses: list,
    weak_clauses: list,
) -> dict:
    """
    根据缺失条款与弱条款数量生成合同完整性检查结果。
    规则：missing >= 3 -> low；missing 1~2 或 weak >= 2 -> medium；missing == 0 且 weak <= 1 -> high。
    返回: completeness_level, missing_clause_count, weak_clause_count, total_issue_count, completeness_summary。
    """
    missing_count = len(missing_clauses) if missing_clauses else 0
    weak_count = len(weak_clauses) if weak_clauses else 0
    total = missing_count + weak_count

    if missing_count >= 3:
        level = "low"
    elif missing_count >= 1 or weak_count >= 2:
        level = "medium"
    else:
        level = "high"

    summary = COMPLETENESS_SUMMARY_MAP.get(level, COMPLETENESS_SUMMARY_MAP["medium"])
    return {
        "completeness_level": level,
        "missing_clause_count": missing_count,
        "weak_clause_count": weak_count,
        "total_issue_count": total,
        "completeness_summary": summary,
    }
