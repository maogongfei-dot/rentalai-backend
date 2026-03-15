# Module3 Phase4-3：风险条款识别（Risk Clause Detection）
# 基于 clause_blocks 识别可能存在风险的条款，输出结构化 risk_clauses，为后续重点条款提示与缺失条款检测做准备。
# 规则与 module3_risk_result 的 risk flag 风格一致，采用基础关键词匹配。

# 条款级风险规则：(risk_flag, 关键词/短语列表, why_flagged 简短说明)
# 与 Module3 RISK_FLAGS_ORDER / RISK_KEYWORDS 对齐
CLAUSE_RISK_RULES = [
    (
        "deposit_risk",
        [
            "deposit", "deduction", "protected", "scheme", "tenancy deposit",
            "holding deposit", "non-refundable", "deposit return", "押金",
        ],
        "条款涉及押金、扣除或押金保护/处理规则。",
    ),
    (
        "rent_increase_risk",
        [
            "increase rent", "review rent", "raise rent", "rent increase",
            "one month notice", "rent rise", "涨租", "加租",
        ],
        "条款涉及涨租、租金调整或通知方式。",
    ),
    (
        "notice_risk",
        [
            "terminate", "notice", "break clause", "end tenancy",
            "notice period", "giving notice", "leave notice", "提前通知",
        ],
        "条款涉及解约、通知期或提前终止。",
    ),
    (
        "eviction_risk",
        [
            "eviction", "section 21", "section 8", "possession",
            "evict", "forced to leave", "驱逐",
        ],
        "条款涉及收回房屋或驱逐程序。",
    ),
    (
        "repair_risk",
        [
            "repair", "maintain", "maintenance", "damage", "responsibility",
            "broken", "mould", "damp", "leak", "维修", "漏水", "发霉",
        ],
        "条款涉及维修责任、损坏或维护义务。",
    ),
    (
        "fee_charge_risk",
        [
            "fee", "charge", "administration fee", "admin fee", "penalty",
            "late fee", "check-out fee", "inventory fee", "费用", "收费",
        ],
        "条款涉及费用、收费或罚金。",
    ),
    (
        "unfair_clause",
        [
            "landlord may at any time", "sole discretion", "final decision",
            "at the landlord's discretion", "exclusively decided", "单方决定",
        ],
        "条款含有单方任意权或最终解释权等表述。",
    ),
]


def _normalize_text(text) -> str:
    """统一小写、去首尾空白，便于匹配。"""
    if text is None:
        return ""
    return str(text).strip().lower()


def _match_risk_flags(text: str) -> list[str]:
    """对条款文本做关键词匹配，返回命中的 risk_flags 列表（保持规则顺序、不重复）。"""
    t = _normalize_text(text)
    if not t:
        return []
    matched = []
    for flag, keywords, _ in CLAUSE_RISK_RULES:
        if flag in matched:
            continue
        for kw in keywords:
            if kw and kw.strip() and kw.lower() in t:
                matched.append(flag)
                break
    return matched


def _risk_level_from_flags(risk_flags: list) -> str:
    """根据命中数量定 risk_level：1 -> low, 2 -> medium, 3+ -> high。"""
    n = len(risk_flags or [])
    if n >= 3:
        return "high"
    if n == 2:
        return "medium"
    if n == 1:
        return "low"
    return "low"


def _build_why_flagged(risk_flags: list) -> str:
    """根据命中的 risk_flags 拼一段简短的 why_flagged 说明。"""
    if not risk_flags:
        return ""
    reasons = []
    for flag in risk_flags:
        for f, _, why in CLAUSE_RISK_RULES:
            if f == flag:
                reasons.append(why)
                break
    return " ".join(reasons) if reasons else "条款命中相关风险关键词。"


def detect_risk_clauses(clause_blocks: list[dict]) -> list[dict]:
    """
    对已切分的 clause_blocks 做风险识别，返回带 risk_flags、risk_level、why_flagged 的列表。
    仅输出至少命中 1 个 risk_flag 的 block；结构含 block_id、page、section_title、text、risk_flags、risk_level、why_flagged。
    """
    if not clause_blocks or not isinstance(clause_blocks, list):
        return []
    out = []
    for block in clause_blocks:
        if not isinstance(block, dict):
            continue
        text = block.get("text") or ""
        risk_flags = _match_risk_flags(text)
        if not risk_flags:
            continue
        out.append({
            "block_id": block.get("block_id", ""),
            "page": block.get("page"),
            "section_title": block.get("section_title") or "",
            "text": text,
            "risk_flags": risk_flags,
            "risk_level": _risk_level_from_flags(risk_flags),
            "why_flagged": _build_why_flagged(risk_flags),
        })
    return out
