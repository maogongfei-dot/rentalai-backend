# Module3 Phase5 Final：缺失条款与完整性输出收口
# 将 Phase5 的 missing_clauses、weak_clauses、contract_completeness 统一为稳定结构 completeness_block，便于前端展示与后续扩展。

def build_completeness_block(
    missing_clauses: list,
    weak_clauses: list,
    contract_completeness: dict,
) -> dict:
    """
    将缺失条款、弱条款与合同完整性检查结果整理为稳定输出结构。
    返回: { missing_clauses, weak_clauses, contract_completeness }。
    """
    return {
        "missing_clauses": list(missing_clauses) if missing_clauses else [],
        "weak_clauses": list(weak_clauses) if weak_clauses else [],
        "contract_completeness": dict(contract_completeness) if contract_completeness else {
            "completeness_level": "",
            "missing_clause_count": 0,
            "weak_clause_count": 0,
            "total_issue_count": 0,
            "completeness_summary": "",
        },
    }
