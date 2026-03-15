# Module3 Phase5-2：弱条款检测（Weak Clause Detection）
# 检查合同中虽存在但内容过模糊、过弱或不完整的条款，输出 weak_clauses，为合同完整性检查做准备。
# 仅对“已存在”的条款类型做弱检测，完全缺失的条款只出现在 missing_clauses 中。

# 条款类型的“主题”关键词（提到即认为该条款存在）与“强化”关键词（具备则不算弱）、why_weak 说明
WEAK_CLAUSE_RULES = [
    (
        "deposit_clause",
        ["deposit", "tenancy deposit", "押金"],
        ["protected", "scheme", "protection", "保护"],
        "条款提到了押金，但未明确保护机制或相关说明。",
    ),
    (
        "rent_clause",
        ["rent", "payment", "租金", "付款"],
        ["payment date", "monthly", "weekly", "amount", "increase", "review", "due", "每月", "每周", "金额"],
        "条款提到了租金或付款，但缺少付款周期、金额或涨租等关键信息。",
    ),
    (
        "termination_clause",
        ["terminate", "termination", "end tenancy", "break clause", "解约", "终止"],
        ["notice", "notice period", "conditions", "通知", "通知期", "条件"],
        "条款提到解约或终止，但未明确通知要求或条件。",
    ),
    (
        "repair_clause",
        ["repair", "maintain", "maintenance", "damage", "维修", "维护"],
        ["landlord", "tenant", "responsibility", "房东", "租客", "责任"],
        "条款提到维修或维护，但未明确责任主体。",
    ),
    (
        "notice_clause",
        ["notice", "通知"],
        ["written", "notice period", "days", "months", "书面", "通知期", "天", "月"],
        "条款提到了通知，但未明确书面形式或通知期限。",
    ),
]


def _block_text_normalized(block: dict) -> str:
    """将 block 的 text 与 section_title 合并为小写字符串便于匹配。"""
    if not block or not isinstance(block, dict):
        return ""
    t = (block.get("text") or "").strip()
    s = (block.get("section_title") or "").strip()
    return " ".join([t, s]).lower()


def find_blocks_by_keywords(clause_blocks: list[dict], keywords: list[str]) -> list[dict]:
    """
    返回 clause_blocks 中 text 或 section_title 包含任一 keyword 的 block 列表（不区分大小写）。
    """
    if not clause_blocks or not keywords:
        return []
    out = []
    for b in clause_blocks:
        if not isinstance(b, dict):
            continue
        combined = _block_text_normalized(b)
        if not combined:
            continue
        for kw in keywords:
            if kw and kw.strip() and kw.lower() in combined:
                out.append(b)
                break
    return out


def _block_has_any_keyword(block: dict, keywords: list[str]) -> bool:
    """block 的 text/section_title 是否包含任一 keyword。"""
    combined = _block_text_normalized(block)
    if not combined or not keywords:
        return False
    for kw in keywords:
        if kw and kw.strip() and kw.lower() in combined:
            return True
    return False


def is_deposit_clause_weak(block: dict) -> bool:
    """deposit 条款是否弱：提到押金但无保护/机制相关表述。"""
    topic = ["deposit", "tenancy deposit", "押金"]
    strong = ["protected", "scheme", "protection", "保护"]
    return _block_has_any_keyword(block, topic) and not _block_has_any_keyword(block, strong)


def _is_clause_weak_for_type(block: dict, topic_keywords: list, strong_keywords: list) -> bool:
    """通用：block 有主题关键词但无强化关键词则判为弱。"""
    return _block_has_any_keyword(block, topic_keywords) and not _block_has_any_keyword(block, strong_keywords)


def detect_weak_clauses(clause_blocks: list[dict]) -> list[dict]:
    """
    对已存在的条款类型，找出内容过弱或不完整的 block，返回 weak_clauses。
    仅当某条款类型在 clause_blocks 中有提及（有 topic 关键词）时才做弱检测；完全缺失的不在此列出。
    返回项：{ clause_type, status: "weak", page, section_title, text, why_weak }。
    """
    if not clause_blocks:
        return []
    out = []
    for clause_type, topic_kw, strong_kw, why_weak in WEAK_CLAUSE_RULES:
        blocks_with_topic = find_blocks_by_keywords(clause_blocks, topic_kw)
        if not blocks_with_topic:
            continue
        for b in blocks_with_topic:
            if not _is_clause_weak_for_type(b, topic_kw, strong_kw):
                continue
            out.append({
                "clause_type": clause_type,
                "status": "weak",
                "page": b.get("page"),
                "section_title": (b.get("section_title") or "").strip(),
                "text": (b.get("text") or "").strip(),
                "why_weak": why_weak,
            })
    return out
