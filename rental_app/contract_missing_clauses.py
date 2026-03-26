"""
Phase B6：关键条款完整性检查（rule-based，关键词 / 正则）。
与风险扫描独立：关注「有没有写清、是否可执行」，而非仅风险词命中。
"""

from __future__ import annotations

import re
from typing import Any

# ---------------------------------------------------------------------------
# 条款清单：每类 primary + 细节子组（present 需 primary 且各子组有足够信号）
# ---------------------------------------------------------------------------

_DEPOSIT_PRIMARY = re.compile(
    r"\bdeposit\b|security\s+deposit|tenancy\s+deposit|holding\s+deposit",
    re.IGNORECASE,
)
_DEPOSIT_RETURN = re.compile(
    r"refund|return|repay|refundable|repayment|within\s+\d+|end\s+of\s+the\s+tenancy",
    re.IGNORECASE,
)
_DEPOSIT_DEDUCT = re.compile(
    r"deduction|deduct|withhold|from\s+(the\s+)?deposit|damage|default|arrears",
    re.IGNORECASE,
)
_DEPOSIT_PROTECT = re.compile(
    r"deposit\s+protection|tenancy\s+deposit\s+scheme|\bTDS\b|\bDPS\b|mydeposits|custodial",
    re.IGNORECASE,
)

_RENT_PRIMARY = re.compile(
    r"\brent\b|rental\s+payment|monthly\s+rent|weekly\s+rent",
    re.IGNORECASE,
)
_RENT_AMOUNT = re.compile(
    r"£\s*\d+|\d+\s*(?:per\s+)?(?:month|week|pcm|pw|calendar\s+month)|"
    r"amount\s+of\s+(?:the\s+)?rent|rent\s+is|rent\s+of",
    re.IGNORECASE,
)
_RENT_CYCLE = re.compile(
    r"payable\s+(?:in\s+)?(?:advance|monthly|weekly)|per\s+calendar\s+month|"
    r"due\s+(?:on|each)|payment\s+date|standing\s+order",
    re.IGNORECASE,
)
_RENT_INCREASE = re.compile(
    r"rent\s+increase|increase\s+(?:in\s+)?rent|rent\s+review|review\s+of\s+rent|"
    r"annual\s+review|CPI|fixed\s+(?:for|during)\s+(?:the\s+)?term|no\s+increase",
    re.IGNORECASE,
)

_REPAIR_LANDLORD = re.compile(
    r"landlord\s+(?:shall|will|is\s+to|agrees\s+to).{0,80}?(?:repair|maintain|structure)",
    re.IGNORECASE | re.DOTALL,
)
_REPAIR_TENANT = re.compile(
    r"tenant\s+(?:shall|will|is\s+to|responsible).{0,80}?(?:repair|maintain|upkeep)",
    re.IGNORECASE | re.DOTALL,
)
_REPAIR_GENERIC = re.compile(
    r"\brepairs?\b|\bmaintenance\b|landlord\s+responsible|tenant\s+responsible",
    re.IGNORECASE,
)

_TERM_BREAK = re.compile(
    r"break\s+clause|terminate|termination|end\s+(?:the\s+)?tenancy|"
    r"early\s+termination|notice\s+to\s+quit|surrender",
    re.IGNORECASE,
)
_TERM_CONDITION = re.compile(
    r"upon\s+expir|after\s+\d+|minimum\s+\d+|condition|unless|if\s+the\s+tenant|"
    r"if\s+the\s+landlord|break\s+date|fixed\s+term",
    re.IGNORECASE,
)

_NOTICE_PERIOD = re.compile(
    r"notice\s+period|\d+\s*(?:month|months|week|weeks|day|days)['']?s?\s+notice|"
    r"one\s+month|two\s+months|at\s+least\s+\d+",
    re.IGNORECASE,
)
_NOTICE_METHOD = re.compile(
    r"written\s+notice|notice\s+in\s+writing|email|recorded\s+delivery|"
    r"served\s+(?:on|at)|address\s+for\s+service",
    re.IGNORECASE,
)

_FEE_GENERIC = re.compile(
    r"\bfee\b|admin(?:istration|istrative)?\s+fee|cleaning\s+fee|service\s+charge|"
    r"late\s+payment|default\s+fee|additional\s+charge|extra\s+charge",
    re.IGNORECASE,
)
_FEE_TRIGGER = re.compile(
    r"if\s+|when\s+|in\s+the\s+event|upon\s+|where\s+the|trigger|payable\s+if|"
    r"shall\s+be\s+payable|only\s+if|provided\s+that",
    re.IGNORECASE,
)

_SCOPE_TERM = re.compile(
    r"fixed\s+term|tenancy\s+term|term\s+of\s+(?:the\s+)?tenancy|commencing|"
    r"from\s+\d|until\s+\d|period\s+of\s+\d+|duration",
    re.IGNORECASE,
)
_SCOPE_PROPERTY = re.compile(
    r"\bpremises\b|\bproperty\b|flat|house|address|at\s+the\s+property|"
    r"dwelling|accommodation\s+known\s+as",
    re.IGNORECASE,
)

# 用于 completeness_level：这些缺失时整体风险更高
_CRITICAL_KEYS = frozenset(
    {"deposit_terms", "rent_terms", "basic_property_or_tenancy_scope"}
)


def _text(t: str) -> str:
    return (t or "").strip()


def _eval_deposit_terms(t: str) -> tuple[str, str, str, str]:
    """押金：primary + 退还 + 扣款依据 + 保护机制。"""
    if not _DEPOSIT_PRIMARY.search(t):
        return (
            "missing",
            "合同中未发现押金（deposit）相关表述",
            "建议明确押金金额、托管/保护安排、退还与扣减条件",
            "high",
        )
    has_ret = bool(_DEPOSIT_RETURN.search(t))
    has_ded = bool(_DEPOSIT_DEDUCT.search(t))
    has_prot = bool(_DEPOSIT_PROTECT.search(t))
    # 扣款依据 + 法定/计划托管，通常已隐含退还路径 → 视为完整
    if has_ret and has_ded and has_prot:
        return ("present", "", "", "low")
    if has_ded and has_prot:
        return ("present", "", "", "low")
    if has_ret and has_ded:
        return (
            "partial_missing",
            "合同提到押金，但押金保护计划或托管安排未明确",
            "建议核对当地法定的押金保护（如适用）并书面确认托管方与证书",
            "medium",
        )
    if has_ret or has_ded:
        return (
            "partial_missing",
            "合同提到押金，但退还条件或扣款依据未同时写清",
            "建议补充押金退还时限、扣减清单及争议处理",
            "medium",
        )
    return (
        "partial_missing",
        "合同提到押金，但未明确退还条件与扣款依据",
        "建议补充押金退还流程、扣款条件及保护机制说明",
        "medium",
    )


def _eval_rent_terms(t: str) -> tuple[str, str, str, str]:
    """租金：金额、支付周期、涨租/固定规则。"""
    if not _RENT_PRIMARY.search(t):
        return (
            "missing",
            "合同中未发现租金（rent）相关表述",
            "建议写明租金金额、币种、支付周期与到期日",
            "high",
        )
    has_amt = bool(_RENT_AMOUNT.search(t))
    has_cyc = bool(_RENT_CYCLE.search(t))
    has_inc = bool(_RENT_INCREASE.search(t))
    if has_amt and has_cyc and has_inc:
        return ("present", "", "", "low")
    if has_amt and has_cyc:
        return (
            "partial_missing",
            "已写明租金与支付周期，但涨租或租期内租金调整规则不明确",
            "建议补充涨租条件、频率、上限或固定租期内是否不变",
            "medium",
        )
    if has_amt or has_cyc:
        return (
            "partial_missing",
            "租金条款不完整：金额或支付周期未同时写清",
            "建议补充具体金额、应付日与支付方式（如 standing order）",
            "medium",
        )
    return (
        "partial_missing",
        "虽提及租金，但未明确金额与支付周期",
        "建议写明周租/月租数额、支付频率与应付日期",
        "medium",
    )


def _eval_repair_responsibility(t: str) -> tuple[str, str, str, str]:
    """维修：房东与租客责任是否均有表述。"""
    if not _REPAIR_GENERIC.search(t):
        return (
            "missing",
            "合同中未发现维修或维护（repairs/maintenance）相关表述",
            "建议明确结构、设施与日常维护的责任划分",
            "high",
        )
    has_l = bool(
        _REPAIR_LANDLORD.search(t)
        or re.search(r"landlord\s+responsible|landlord\s+.{0,50}?(?:structure|repair|exterior)", t, re.I | re.DOTALL)
    )
    has_tn = bool(
        _REPAIR_TENANT.search(t)
        or re.search(
            r"tenant\s+responsible|tenant\s+.{0,60}?(?:maintenance|repair|upkeep|minor)",
            t,
            re.I | re.DOTALL,
        )
    )
    if has_l and has_tn:
        return ("present", "", "", "low")
    if has_l or has_tn:
        return (
            "partial_missing",
            "仅单方维修责任表述较明确，另一方责任边界可能不清",
            "建议用清单区分房东（结构/外墙等）与租客（日常损耗/清洁）责任",
            "medium",
        )
    return (
        "partial_missing",
        "提及维修/维护，但未清晰区分房东与租客责任",
        "建议补充 landlord/tenant 各自义务范围",
        "medium",
    )


def _eval_termination_terms(t: str) -> tuple[str, str, str, str]:
    """解约：提前终止 / break + 条件或通知。"""
    if not _TERM_BREAK.search(t):
        return (
            "missing",
            "合同中未发现提前解约、终止或 break clause 等表述",
            "建议写明提前终止条件、通知期与费用（如有）",
            "high",
        )
    has_cond = bool(_TERM_CONDITION.search(t))
    if has_cond:
        return ("present", "", "", "low")
    return (
        "partial_missing",
        "提及终止或解约，但条件、期限或触发情形不够具体",
        "建议补充 break date、通知要求与违约情形下的处理",
        "medium",
    )


def _eval_notice_terms(t: str) -> tuple[str, str, str, str]:
    """通知：通知期 + 方式。"""
    has_p = bool(_NOTICE_PERIOD.search(t))
    has_m = bool(_NOTICE_METHOD.search(t))
    if not has_p and not has_m:
        return (
            "missing",
            "合同中未发现明确通知期或通知方式",
            "建议补充 notice period、书面通知方式及生效规则",
            "high",
        )
    if has_p and has_m:
        return ("present", "", "", "low")
    return (
        "partial_missing",
        "通知条款不完整：通知期与书面/送达方式未同时写清",
        "建议写明提前多久、以何种方式送达、送达地址",
        "medium",
    )


def _eval_fee_terms(t: str) -> tuple[str, str, str, str]:
    """杂费：若列了收费项，需有触发/前提；未列任何杂费则视为已覆盖（不强制列出）。"""
    if not _FEE_GENERIC.search(t):
        return ("present", "", "", "low")
    if _FEE_TRIGGER.search(t):
        return ("present", "", "", "low")
    return (
        "partial_missing",
        "提及费用或收费，但触发条件或支付前提不够清楚",
        "建议逐项列明费用名称、金额、何时产生、是否可退",
        "medium",
    )


def _eval_basic_scope(t: str) -> tuple[str, str, str, str]:
    """租期与标的范围。"""
    has_term = bool(_SCOPE_TERM.search(t))
    has_prop = bool(_SCOPE_PROPERTY.search(t))
    if has_term and has_prop:
        return ("present", "", "", "low")
    if has_term or has_prop:
        return (
            "partial_missing",
            "租期或租赁标的描述仅部分出现，整体范围可能不够清楚",
            "建议确认起止日期/周期与房产地址或描述一致",
            "medium",
        )
    return (
        "missing",
        "未发现清晰的租期（term）或房产/标的（property/premises）描述",
        "建议写明固定租期起止日与租赁物地址或清晰描述",
        "high",
    )


_EVALUATORS = {
    "deposit_terms": _eval_deposit_terms,
    "rent_terms": _eval_rent_terms,
    "repair_responsibility": _eval_repair_responsibility,
    "termination_terms": _eval_termination_terms,
    "notice_terms": _eval_notice_terms,
    "fee_terms": _eval_fee_terms,
    "basic_property_or_tenancy_scope": _eval_basic_scope,
}


def detect_missing_clauses(contract_text: str) -> list[dict[str, Any]]:
    """
    条款完整性检查：返回仅含 status 为 missing / partial_missing 的条目（present 不列出）。
    每条含 clause_key, status, severity, reason, suggestion。
    """
    t = _text(contract_text)

    out: list[dict[str, Any]] = []
    for clause_key, fn in _EVALUATORS.items():
        status, reason, suggestion, sev = fn(t)
        # missing / partial_missing / present 判断逻辑：仅输出需关注的问题
        if status == "present":
            continue
        out.append(
            {
                "clause_key": clause_key,
                "status": status,
                "severity": sev,
                "reason": reason,
                "suggestion": suggestion,
            }
        )
    return out


def _completeness_level_and_note(
    all_statuses: dict[str, str],
) -> tuple[str, str, int, int]:
    """
    根据各条款 status 汇总 completeness_level 与 completeness_note。
    """
    missing_n = sum(1 for s in all_statuses.values() if s == "missing")
    partial_n = sum(1 for s in all_statuses.values() if s == "partial_missing")
    critical_missing = any(
        all_statuses.get(k) == "missing" for k in _CRITICAL_KEYS
    )

    # 简单分级：关键条款缺失或多个缺失 → low；以 partial 为主 → medium；否则 high
    if critical_missing or missing_n >= 2:
        level = "low"
    elif missing_n >= 1 or partial_n >= 4:
        level = "medium"
    elif partial_n >= 2:
        level = "medium"
    else:
        level = "high"

    _LABELS = {
        "deposit_terms": "押金",
        "rent_terms": "租金",
        "repair_responsibility": "维修责任",
        "termination_terms": "解约/终止",
        "notice_terms": "通知",
        "fee_terms": "杂费",
        "basic_property_or_tenancy_scope": "租期与标的",
    }
    miss_keys = [k for k, s in all_statuses.items() if s == "missing"]
    part_keys = [k for k, s in all_statuses.items() if s == "partial_missing"]

    if not miss_keys and not part_keys:
        note = "核心条款在文本中有较完整表述，仍建议人工核对全文与适用法律。"
    elif level == "low":
        seg = []
        if miss_keys:
            seg.append("未覆盖：" + "、".join(_LABELS.get(k, k) for k in miss_keys))
        if part_keys:
            seg.append("不完整：" + "、".join(_LABELS.get(k, k) for k in part_keys))
        note = "合同完整性偏低。" + "；".join(seg) + "。"
    elif level == "medium":
        seg = []
        if miss_keys:
            seg.append("未覆盖：" + "、".join(_LABELS.get(k, k) for k in miss_keys))
        if part_keys:
            seg.append("表述不清：" + "、".join(_LABELS.get(k, k) for k in part_keys))
        note = "合同已覆盖部分核心条款，但" + "；".join(seg) + "，建议补充或澄清。"
    else:
        # high：至多 1 项 partial
        if part_keys:
            note = (
                "整体较完整；"
                + _LABELS.get(part_keys[0], part_keys[0])
                + "仍可进一步细化，建议人工复核。"
            )
        else:
            note = "核心条款在文本中有较完整表述，仍建议人工核对全文与适用法律。"

    return level, note, missing_n, partial_n


def analyze_all_clause_statuses(contract_text: str) -> dict[str, str]:
    """内部用：每条 clause_key → present | partial_missing | missing（含全部七类）。"""
    t = _text(contract_text)
    st: dict[str, str] = {}
    for clause_key, fn in _EVALUATORS.items():
        status, _, _, _ = fn(t)
        st[clause_key] = status
    return st


def build_completeness_summary(contract_text: str) -> dict[str, Any]:
    """
    生成 summary 中的完整性字段：计数 + completeness_level + completeness_note。
    """
    t = _text(contract_text)
    all_statuses = analyze_all_clause_statuses(t)
    level, note, missing_n, partial_n = _completeness_level_and_note(all_statuses)
    if not t:
        note = "合同文本为空。" + note
    return {
        "missing_clause_count": missing_n,
        "partial_missing_count": partial_n,
        "completeness_level": level,
        "completeness_note": note,
    }
