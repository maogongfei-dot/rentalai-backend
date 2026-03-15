# Module3 Phase5-1：缺失条款检测（Missing Clause Detection）
# 根据 clause_blocks 检查合同中哪些必要条款未被识别，输出 missing_clauses，为弱条款检测与合同完整性检查做准备。

# 必要条款类型及对应关键词、缺失说明（基础规则版）
REQUIRED_CLAUSE_RULES = [
    (
        "deposit_clause",
        ["deposit", "tenancy deposit", "protected", "scheme", "押金"],
        "合同中未明显识别到押金相关条款。",
    ),
    (
        "rent_clause",
        ["rent", "payment", "monthly rent", "weekly rent", "租金", "付款"],
        "合同中未明显识别到租金/付款相关条款。",
    ),
    (
        "termination_clause",
        ["terminate", "termination", "end tenancy", "break clause", "解约", "终止"],
        "合同中未明显识别到解约/终止相关条款。",
    ),
    (
        "repair_clause",
        ["repair", "maintain", "maintenance", "damage", "responsibility", "维修", "维护"],
        "合同中未明显识别到维修/维护责任相关条款。",
    ),
    (
        "notice_clause",
        ["notice", "written notice", "notice period", "通知", "通知期"],
        "合同中未明显识别到通知相关条款。",
    ),
]


def has_clause_keywords(clause_blocks: list[dict], keywords: list[str]) -> bool:
    """
    检查 clause_blocks 中是否存在任一 block 的 text 或 section_title 包含任一关键词（不区分大小写）。
    若 blocks 为空或无有效关键词，返回 False。
    """
    if not clause_blocks or not keywords:
        return False
    text_parts = []
    for b in clause_blocks:
        if not isinstance(b, dict):
            continue
        t = (b.get("text") or "").strip()
        s = (b.get("section_title") or "").strip()
        if t:
            text_parts.append(t.lower())
        if s:
            text_parts.append(s.lower())
    combined = " ".join(text_parts)
    if not combined:
        return False
    for kw in keywords:
        if kw and kw.strip() and kw.lower() in combined:
            return True
    return False


def detect_missing_clauses(clause_blocks: list[dict]) -> list[dict]:
    """
    根据 clause_blocks 的 text 与 section_title 判断各必要条款是否存在；
    未命中关键词的条款类型加入返回列表，结构为 { clause_type, status: "missing", why_missing }。
    """
    if not clause_blocks and clause_blocks is not None:
        clause_blocks = []
    out = []
    for clause_type, keywords, why_missing in REQUIRED_CLAUSE_RULES:
        if has_clause_keywords(clause_blocks, keywords):
            continue
        out.append({
            "clause_type": clause_type,
            "status": "missing",
            "why_missing": why_missing,
        })
    return out
