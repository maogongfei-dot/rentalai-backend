"""
合同文本分析（Phase B1/B2/B3）：rule-based 风险识别入口，不接 LLM。
Phase B2：句子级 matched_text、explanation、recommendation_action 等。
Phase B3：contract_legal_mapping 提供 legal_context 与 summary_note（法律解释映射层，非正式法律意见）。
Phase B4：contract_action_mapping 提供 action_priority、checklist、提问、证据与 summary.next_step_summary。
"""

from __future__ import annotations

import re
from typing import Any, Optional

from contract_action_mapping import build_next_step_summary, enrich_risk_with_actions
from contract_legal_mapping import build_summary_note, enrich_risk_with_legal_context

# --- 风险主题（与 API risk_type 一致）---
RISK_TYPE_DEPOSIT = "deposit"
RISK_TYPE_RENT_INCREASE = "rent_increase"
RISK_TYPE_REPAIRS = "repairs"
RISK_TYPE_TERMINATION = "termination"
RISK_TYPE_FEES = "fees"
RISK_TYPE_NOTICE = "notice"

_SEV_ORDER = {"low": 1, "medium": 2, "high": 3}


def _compile(exprs: list[str]):
    return [re.compile(e, re.IGNORECASE | re.DOTALL) for e in exprs]


# ---------------------------------------------------------------------------
# 句子切分逻辑：按 . ! ? 与换行分段，保留原文 evidence_span
# ---------------------------------------------------------------------------


def _split_sentences(text: str) -> list[tuple[str, int, int]]:
    """
    将合同文本拆成句级片段，每项为 (句子文本, 在全文中的 start, end)。
    边界：句号/问号/叹号后空白、或单独成行；过短片段会与相邻合并由调用方处理。
    """
    out: list[tuple[str, int, int]] = []
    if not (text or "").strip():
        return out
    # 非贪婪匹配到句末标点或行尾
    for m in re.finditer(r"[^\n.!?]+[.!?]?|[^\n.!?]+(?=\n|$)", text):
        raw = m.group().strip()
        if not raw:
            continue
        out.append((raw, m.start(), m.end()))
    if not out:
        out.append((text.strip(), 0, len(text)))
    return out


def _expand_matched_text(
    sentences: list[tuple[str, int, int]],
    idx: int,
) -> tuple[str, int, int]:
    """
    matched_text 提取：优先整句；若过短则拼接后一句作为上下文（仍返回合并后的 span）。
    """
    sent, s0, e0 = sentences[idx]
    if len(sent) >= 50 or idx + 1 >= len(sentences):
        return sent, s0, e0
    s2, s1, e1 = sentences[idx + 1]
    merged = (sent + " " + s2).strip()
    return merged, s0, e1


# ---------------------------------------------------------------------------
# 扩展关键词 / 正则（Phase B2）
# ---------------------------------------------------------------------------

# --- deposit ---
_DEPOSIT_HIGH = _compile(
    [
        r"non[-\s]?refundable\s+deposit",
        r"deposit\s+will\s+not\s+be\s+returned",
        r"deposit\s+not\s+returned\s+under\s+any\s+circumstances",
        r"deposit\s+is\s+not\s+refundable",
        r"forfeit\s+.{0,40}deposit",
    ]
)
_DEPOSIT_MED = _compile(
    [
        r"deductions?\s+from\s+(the\s+)?deposit",
        r"deposit\s+.{0,80}(refund|return|repay)",
        r"deposit\s+protection",
        r"tenancy\s+deposit\s+scheme",
    ]
)
_DEPOSIT_LOW = _compile(
    [
        r"\bdeposit\b",
        r"security\s+deposit",
        r"refundable\s+deposit",
        r"tenancy\s+deposit",
    ]
)

# --- rent_increase ---
_RENT_HIGH = _compile(
    [
        r"landlord\s+may\s+increase\s+(the\s+)?rent\s+at\s+any\s+time",
        r"increase\s+(the\s+)?rent\s+at\s+any\s+time",
        r"rent\s+may\s+be\s+increased\s+without\s+limit",
        r"可单方随时涨租",
        r"房东可随时涨租",
    ]
)
_RENT_MED = _compile(
    [
        r"landlord\s+may\s+increase\s+rent",
        r"rent\s+may\s+be\s+reviewed\s+annually",
        r"rent\s+review",
        r"review\s+of\s+rent",
        r"change\s+of\s+rent",
        r"revised\s+rent",
        r"annual\s+review",
    ]
)
_RENT_LOW = _compile(
    [
        r"rent\s+increase",
        r"increase\s+the\s+rent",
        r"review\s+the\s+rent",
        r"increase\s+in\s+rent",
    ]
)

# --- repairs ---
_REP_HIGH = _compile(
    [
        r"tenant\s+responsible\s+for\s+all\s+repairs",
        r"tenant\s+shall\s+keep\s+.{0,60}in\s+repair",
        r"landlord\s+is\s+not\s+responsible\s+for\s+.{0,40}repairs?",
        r"landlord\s+not\s+responsible\s+for\s+repairs?",
    ]
)
_REP_MED = _compile(
    [
        r"maintenance\s+cost",
        r"tenant\s+responsible",
        r"landlord\s+responsible",
        r"repair\s+responsibility",
    ]
)
_REP_LOW = _compile([r"\brepairs?\b", r"\bmaintenance\b"])

# --- termination ---
_TERM_HIGH = _compile(
    [
        r"early\s+termination\s+fee",
        r"termination\s+fee\s+.{0,40}(substantial|penalty|forfeit)",
        r"landlord\s+may\s+terminate\s+.{0,40}without\s+cause",
        r"landlord\s+.{0,40}unilateral\s+termination",
    ]
)
_TERM_MED = _compile(
    [
        r"either\s+party\s+may\s+terminate",
        r"break\s+clause",
        r"end\s+the\s+tenancy\s+early",
        r"early\s+termination",
        r"terminate\s+the\s+tenancy",
    ]
)
_TERM_LOW = _compile(
    [
        r"\bterminate\b",
        r"\btermination\b",
    ]
)

# --- fees ---
_FEES_HIGH = _compile(
    [
        r"non[-\s]?refundable\s+fee",
        r"cleaning\s+fee\s+.{0,40}(mandatory|regardless|whether)",
        r"(?:administration|administrative)\s+fee.{0,60}(?:late|default|additional)",
    ]
)
_FEES_MED = _compile(
    [
        r"administration\s+fee",
        r"administrative\s+fee",
        r"service\s+charge",
        r"late\s+payment\s+fee",
        r"default\s+fee",
        r"professional\s+cleaning\s+fee",
        r"extra\s+charge",
    ]
)
_FEES_LOW = _compile([r"\bfee\b", r"charges?\b"])

# --- notice ---
_NOT_HIGH = _compile(
    [
        r"tenant\s+.{0,40}notice\s+.{0,40}(waive|not\s+required|deemed\s+waiver)",
        r"landlord\s+only\s+.{0,60}notice",
    ]
)
_NOT_MED = _compile(
    [
        r"one\s+month'?s?\s+notice",
        r"two\s+months?'?\s+notice",
        r"written\s+notice",
        r"notice\s+in\s+writing",
        r"notice\s+must\s+be\s+served",
        r"notice\s+period\s+.{0,40}(unclear|tbc|tbd)",
    ]
)
_NOT_LOW = _compile([r"notice\s+period", r"\bnotice\b"])


def _first_severity_in_sentence(sent: str, high, med, low) -> Optional[str]:
    """在同一句内按 high > med > low 命中顺序返回严重度。"""
    for rx in high:
        if rx.search(sent):
            return "high"
    for rx in med:
        if rx.search(sent):
            return "medium"
    for rx in low:
        if rx.search(sent):
            return "low"
    return None


# ---------------------------------------------------------------------------
# severity 增强规则：在句级命中后按主题微调（Phase B2）
# ---------------------------------------------------------------------------


def _adjust_deposit(severity: str, sent: str) -> str:
    sl = sent.lower()
    if severity == "medium":
        if re.search(r"refund|return|repay|protection|scheme", sl):
            return "medium"
        if re.search(r"\bdeposit\b", sl) and not re.search(
            r"refund|return|non[-\s]?refundable|not\s+returned", sl
        ):
            return "medium"
    if severity == "low" and len(sent) > 120:
        return "medium"
    return severity


def _adjust_rent(severity: str, sent: str) -> str:
    sl = sent.lower()
    if severity in ("low", "medium"):
        if re.search(r"notice|consult|reasonable|fair|annual\s+review\s+with", sl):
            if "at any time" not in sl:
                return "low" if severity == "low" else "medium"
    return severity


def _adjust_repairs(severity: str, sent: str) -> str:
    sl = sent.lower()
    if severity == "medium":
        if re.search(r"landlord\s+responsible|tenant\s+responsible", sl):
            if not re.search(r"all\s+repairs|not\s+responsible", sl):
                return "low"
    return severity


def _adjust_termination(severity: str, sent: str) -> str:
    sl = sent.lower()
    if severity == "high":
        if re.search(r"early\s+termination\s+fee|penalty", sl) and len(sent) < 80:
            return "high"
    if severity == "medium" and "break" in sl and "clause" in sl:
        if not re.search(r"condition|notice|month", sl):
            return "medium"
    return severity


def _adjust_fees(severity: str, sent: str) -> str:
    sl = sent.lower()
    fee_hits = len(re.findall(r"\bfee\b|\bcharge\b", sl))
    if fee_hits >= 3 and severity != "high":
        return "high"
    if severity == "medium" and re.search(r"mandatory|regardless|all\s+costs", sl):
        return "high"
    return severity


def _adjust_notice(severity: str, sent: str) -> str:
    sl = sent.lower()
    if severity == "medium":
        if re.search(r"\d+\s*(month|day|week)", sl) and re.search(r"notice", sl):
            if not re.search(r"unclear|tbc|at\s+least", sl):
                return "low"
    return severity


_ADJUSTERS = {
    RISK_TYPE_DEPOSIT: _adjust_deposit,
    RISK_TYPE_RENT_INCREASE: _adjust_rent,
    RISK_TYPE_REPAIRS: _adjust_repairs,
    RISK_TYPE_TERMINATION: _adjust_termination,
    RISK_TYPE_FEES: _adjust_fees,
    RISK_TYPE_NOTICE: _adjust_notice,
}


# ---------------------------------------------------------------------------
# reason / explanation / recommendation_action（生成逻辑）
# ---------------------------------------------------------------------------

_REASON = {
    RISK_TYPE_DEPOSIT: {
        "high": "出现不可退还或没收押金等高风险表述。",
        "medium": "已识别押金相关条款，退还或扣款条件需进一步核实。",
        "low": "提及押金，需结合全文判断金额与保护安排。",
    },
    RISK_TYPE_RENT_INCREASE: {
        "high": "出现房东可随时涨租或类似单边强势表述。",
        "medium": "存在涨租、租金复审或变更条款，条件可能不够清晰。",
        "low": "提及租金调整或复审，需结合通知与公平性判断。",
    },
    RISK_TYPE_REPAIRS: {
        "high": "租客承担全部维修或房东明确不承担维修等表述。",
        "medium": "维修或维护责任划分存在，边界可能模糊。",
        "low": "提及维修或维护义务，责任划分相对常规。",
    },
    RISK_TYPE_TERMINATION: {
        "high": "提前解约费用、违约金或房东单方解约相关表述风险较高。",
        "medium": "存在 break clause 或提前终止，条件或通知可能不清晰。",
        "low": "提及解约或终止程序，需结合通知期判断。",
    },
    RISK_TYPE_FEES: {
        "high": "不可退款费用、多项杂费或强制清洁费等表述需警惕。",
        "medium": "存在行政费、滞纳金或服务费等，触发条件可能不明。",
        "low": "提及费用或收费项目，需核对金额与合理性。",
    },
    RISK_TYPE_NOTICE: {
        "high": "通知条款可能对一方明显不利或试图免除程序。",
        "medium": "通知期或书面形式要求存在但不完整。",
        "low": "列明通知期或书面通知，相对常规。",
    },
}

_EXPLANATION = {
    RISK_TYPE_DEPOSIT: {
        "high": "英国等地通常要求押金进入保护计划；完全不可退押金对租客极为不利，可能违法或需个案审查。",
        "medium": "押金扣减事由、退还时限若未写清，容易产生争议；deposit protection 是否适用需核实。",
        "low": "仅出现押金金额或一般性描述时，需对照当地法规定金上限与托管要求。",
    },
    RISK_TYPE_RENT_INCREASE: {
        "high": "“随时涨租”类条款严重削弱租金可预期性，审查时应要求明确频率、上限与协商程序。",
        "medium": "年度复审、租金审查若未约定上限或通知期，租客议价空间可能不足。",
        "low": "若已约定通知与合理程序，年度调整可能是常见商业条款，仍需核对公平性。",
    },
    RISK_TYPE_REPAIRS: {
        "high": "租客承担“全部”维修或房东完全不承担，可能将结构性风险不合理转嫁给租客。",
        "medium": "责任边界模糊时，建议用清单区分房东/租客各自义务（如结构、家电、日常损耗）。",
        "low": "若条款与惯例责任划分一致，风险相对较低，仍建议保留书面记录。",
    },
    RISK_TYPE_TERMINATION: {
        "high": "高额提前终止费或宽泛违约金可能构成惩罚性条款，需核对是否合法合理。",
        "medium": "Break clause 若未写清触发条件、通知与费用，解约成本不确定。",
        "low": "标准通知期解约通常可接受，仍需确认押金结算与交接。",
    },
    RISK_TYPE_FEES: {
        "high": "多项笼统收费或强制清洁费可能叠加成本；应要求逐项列明金额与触发条件。",
        "medium": "行政费、滞纳金等应核对是否与已披露费用一致，避免重复收费。",
        "low": "小额明确费用在租赁中较常见，重点核对是否与广告/报价一致。",
    },
    RISK_TYPE_NOTICE: {
        "high": "单方面缩短或免除通知可能损害程序正义，应要求对等通知义务与送达方式。",
        "medium": "通知期长度、书面形式与送达地址若不明确，争议时难以举证。",
        "low": "明确月数/周数与书面形式时，可作为后续退租与举证依据。",
    },
}

_RECOMMENDATION_ACTION = {
    RISK_TYPE_DEPOSIT: "要求书面确认押金退还条件、扣款清单及是否进入押金保护机制；保留转账凭证。",
    RISK_TYPE_RENT_INCREASE: "要求确认涨租触发条件、频率、上限与提前通知期；必要时协商写入上限或 CPI 挂钩方式。",
    RISK_TYPE_REPAIRS: "要求用附件列明房东与租客各自维修范围（结构、花园、家电等），并明确紧急维修联络方式。",
    RISK_TYPE_TERMINATION: "核对提前解约、break clause 的费用、通知期与押金结算；有疑问时寻求独立法律意见。",
    RISK_TYPE_FEES: "要求列出全部额外收费项目、金额、触发条件与是否可退；拒绝未列明的口头收费。",
    RISK_TYPE_NOTICE: "确认通知期长度、书面形式、送达地址与生效时间；退租建议用可追踪方式送达。",
}


def _pick_text_maps(risk_type: str, severity: str):
    return (
        _REASON.get(risk_type, {}).get(severity, "已识别相关条款，建议人工复核。"),
        _EXPLANATION.get(risk_type, {}).get(severity, "请结合全文与适用法律判断。"),
        _RECOMMENDATION_ACTION.get(risk_type, "建议逐条核对合同并与对方书面确认不明之处。"),
    )


def _scan_category(
    risk_type: str,
    sentences: list[tuple[str, int, int]],
    high,
    med,
    low,
) -> Optional[dict[str, Any]]:
    """句级扫描：每句取 high>med>low 中最高命中档，再全局选严重度最大的一条（同档取先出现句）。"""
    candidates: list[tuple[int, int, str, str, int, int]] = []
    for idx, (sent, s0, e0) in enumerate(sentences):
        sev = _first_severity_in_sentence(sent, high, med, low)
        if not sev:
            continue
        sev = _ADJUSTERS.get(risk_type, lambda s, _: s)(sev, sent)
        order = _SEV_ORDER.get(sev, 1)
        candidates.append((order, idx, sev, sent, s0, e0))

    if not candidates:
        return None

    candidates.sort(key=lambda x: (-x[0], x[1]))
    _order, idx, severity, _sent, _s0, _e0 = candidates[0]
    matched_text, span0, span1 = _expand_matched_text(sentences, idx)
    severity = _ADJUSTERS.get(risk_type, lambda s, _: s)(severity, matched_text)
    reason, explanation, rec = _pick_text_maps(risk_type, severity)

    return {
        "risk_type": risk_type,
        "severity": severity,
        "matched_text": matched_text,
        "source_excerpt": matched_text,
        "reason": reason,
        "explanation": explanation,
        "recommendation_action": rec,
        "evidence_span": {"start": span0, "end": span1},
    }


def _overall_level(high: int, medium: int, low: int) -> str:
    """有 high 则整体 high；否则任一则 medium 即 medium；否则 low。"""
    if high > 0:
        return "high"
    if medium > 0:
        return "medium"
    return "low"


def analyze_contract_text(contract_text: str) -> dict[str, Any]:
    """
    合同文本分析入口：detected_risks 含 B2/B3/B4 字段；summary 含 summary_note 与 next_step_summary。
    """
    text = contract_text.strip()
    sentences = _split_sentences(text)

    scanners = [
        (RISK_TYPE_DEPOSIT, _DEPOSIT_HIGH, _DEPOSIT_MED, _DEPOSIT_LOW),
        (RISK_TYPE_RENT_INCREASE, _RENT_HIGH, _RENT_MED, _RENT_LOW),
        (RISK_TYPE_REPAIRS, _REP_HIGH, _REP_MED, _REP_LOW),
        (RISK_TYPE_TERMINATION, _TERM_HIGH, _TERM_MED, _TERM_LOW),
        (RISK_TYPE_FEES, _FEES_HIGH, _FEES_MED, _FEES_LOW),
        (RISK_TYPE_NOTICE, _NOT_HIGH, _NOT_MED, _NOT_LOW),
    ]

    detected: list[dict[str, Any]] = []
    for rt, hi, md, lo in scanners:
        item = _scan_category(rt, sentences, hi, md, lo)
        if item:
            detected.append(item)

    # Phase B3：逐条合并法律解释映射
    detected = [enrich_risk_with_legal_context(r) for r in detected]
    # Phase B4：行动建议层（action_priority / checklist / 提问 / 证据）
    detected = [enrich_risk_with_actions(r) for r in detected]

    high_n = sum(1 for r in detected if r.get("severity") == "high")
    med_n = sum(1 for r in detected if r.get("severity") == "medium")
    low_n = sum(1 for r in detected if r.get("severity") == "low")
    types = [r["risk_type"] for r in detected]
    overall = _overall_level(high_n, med_n, low_n)
    summary_note = build_summary_note(detected)
    next_step_summary = build_next_step_summary(detected)

    return {
        "contract_text": text,
        "detected_risks": detected,
        "summary": {
            "risk_count": len(detected),
            "high_risk_count": high_n,
            "medium_risk_count": med_n,
            "low_risk_count": low_n,
            "risk_types": types,
            "overall_level": overall,
            "summary_note": summary_note,
            "next_step_summary": next_step_summary,
        },
    }
