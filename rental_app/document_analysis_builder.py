# Module3 Phase4 Final：文档风险输出收口
# 将 Phase4 文档分析相关字段统一为稳定结构 document_analysis_block，为 Phase5 缺失条款检测做准备。

def build_document_analysis_block(
    document_data: dict,
    clause_blocks: list,
    risk_clauses: list,
    highlighted_clauses: list,
) -> dict:
    """
    将文档读取结果与条款切分、风险条款、重点条款整理为稳定输出结构。
    返回: { document_summary, clause_blocks, risk_clauses, highlighted_clauses }。
    """
    doc = document_data or {}
    summary = {
        "file_name": doc.get("file_name") or "",
        "file_type": doc.get("file_type") or "",
        "block_count": len(clause_blocks) if clause_blocks else 0,
        "risk_clause_count": len(risk_clauses) if risk_clauses else 0,
        "highlighted_clause_count": len(highlighted_clauses) if highlighted_clauses else 0,
    }
    return {
        "document_summary": summary,
        "clause_blocks": list(clause_blocks) if clause_blocks else [],
        "risk_clauses": list(risk_clauses) if risk_clauses else [],
        "highlighted_clauses": list(highlighted_clauses) if highlighted_clauses else [],
    }
