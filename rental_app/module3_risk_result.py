# Module Transition 1: Module3 合同与纠纷风险系统 — 启动准备（骨架与标准结果）
#
# 第一阶段目标（仅风险骨架，不做复杂法律判断）:
#   - 输入: 租房合同/纠纷相关文本或问题
#   - 输出: 基础风险分类、风险摘要、建议下一步动作
#   - 保留未来扩展到更细合同条款分析的空间

from datetime import datetime

MODULE3_VERSION = "module3_risk_baseline_v1"

# ---------- Phase1-A1: 基础风险标签与关键词规则（集中定义） ----------
RISK_FLAGS_ORDER = [
    "deposit_risk",
    "notice_risk",
    "repair_risk",
    "landlord_entry_risk",
    "rent_increase_risk",
    "eviction_risk",
    "fee_charge_risk",
]

RISK_KEYWORDS = {
    "deposit_risk": [
        "deposit", "deposit return", "protected deposit", "tenancy deposit",
        "holding deposit", "non-refundable", "押金", "押金不退",
    ],
    "notice_risk": [
        "notice", "two months notice", "two month notice", "leave notice",
        "notice period", "notice to quit", "giving notice", "提前通知",
    ],
    "repair_risk": [
        "repair", "repaired", "broken", "mould", "mold", "damp", "leak",
        "leaking", "heating", "boiler", "dampness", "漏水", "发霉", "维修",
    ],
    "landlord_entry_risk": [
        "enter", "entry", "access", "inspection without notice",
        "landlord enter", "right to enter", "without notice", "闯入",
    ],
    "rent_increase_risk": [
        "rent increase", "raise rent", "increased rent", "rent rise",
        "rent review", "increase rent", "涨租", "加租",
    ],
    "eviction_risk": [
        "eviction", "section 21", "section 8", "forced to leave",
        "evict", "possession", "kick out", "驱逐", "赶走",
    ],
    "fee_charge_risk": [
        "fee", "charge", "admin fee", "administration fee", "extra cost",
        "penalty", "late fee", "check-out fee", "inventory fee", "费用", "收费",
    ],
}

# ---------- Phase1-A2: 风险解释与推荐动作映射（集中定义） ----------
FLAG_TO_READABLE = {
    "deposit_risk": "deposit",
    "notice_risk": "notice",
    "repair_risk": "repairs",
    "landlord_entry_risk": "landlord entry",
    "rent_increase_risk": "rent increase",
    "eviction_risk": "eviction",
    "fee_charge_risk": "fees or charges",
}

RISK_EXPLANATIONS_MAP = {
    "deposit_risk": {
        "title": "Deposit issue",
        "explanation": "The text may involve deposit protection or deposit return concerns.",
        "actions": [
            "Check whether the deposit is protected in an approved scheme.",
            "Keep payment records and tenancy documents.",
        ],
    },
    "notice_risk": {
        "title": "Notice period issue",
        "explanation": "The text may involve notice to leave or notice period concerns.",
        "actions": [
            "Check the tenancy agreement for the required notice period.",
            "Keep written records of any notice given or received.",
        ],
    },
    "repair_risk": {
        "title": "Repair issue",
        "explanation": "The text may raise maintenance or repair responsibility concerns.",
        "actions": [
            "Document the repair issue with photos and dates.",
            "Check what the tenancy agreement says about repair responsibilities.",
        ],
    },
    "landlord_entry_risk": {
        "title": "Landlord entry / access issue",
        "explanation": "The text may involve landlord access or entry without proper notice.",
        "actions": [
            "Check the tenancy agreement and law on landlord access and notice.",
            "Keep a record of any unauthorised entry or short notice.",
        ],
    },
    "rent_increase_risk": {
        "title": "Rent increase issue",
        "explanation": "The text may involve rent increase or rent review concerns.",
        "actions": [
            "Check whether the rent increase and procedure comply with the tenancy and law.",
            "Keep records of the current rent and any notice of increase.",
        ],
    },
    "eviction_risk": {
        "title": "Eviction / possession issue",
        "explanation": "The text may involve eviction, possession, or being asked to leave.",
        "actions": [
            "Check that any notice or court process is valid (e.g. section 21 / section 8).",
            "Seek advice early if you are at risk of losing your home.",
        ],
    },
    "fee_charge_risk": {
        "title": "Fee or charge issue",
        "explanation": "The text may involve extra fees, charges, or penalties.",
        "actions": [
            "Check the tenancy agreement and law on permitted fees and charges.",
            "Keep receipts and records of any payments demanded.",
        ],
    },
}

DEFAULT_ACTIONS_WHEN_NO_RISK = [
    "Review the full context before drawing a conclusion.",
    "No obvious baseline risk was detected, but you may still want to check the tenancy details carefully.",
]

# ---------- Phase1-A3: 风险严重度与动作优先级（集中定义，默认映射） ----------
RISK_SEVERITY_PRIORITY_MAP = {
    "eviction_risk": {"severity": "high", "priority": "high"},
    "landlord_entry_risk": {"severity": "high", "priority": "high"},
    "deposit_risk": {"severity": "medium", "priority": "medium"},
    "repair_risk": {"severity": "medium", "priority": "medium"},
    "notice_risk": {"severity": "medium", "priority": "medium"},
    "rent_increase_risk": {"severity": "medium", "priority": "medium"},
    "fee_charge_risk": {"severity": "low", "priority": "low"},
}

PRIORITY_ORDER = ("high", "medium", "low")  # 用于 recommended_actions 排序


def _normalize_text(text):
    """Lower-case 标准化，缺输入返回空字符串。"""
    if text is None:
        return ""
    return str(text).strip().lower()


def _detect_risk_flags(text):
    """
    根据关键词/短语匹配返回命中的风险标签，按 RISK_FLAGS_ORDER 顺序、不重复。
    缺输入或空字符串返回 []。
    """
    t = _normalize_text(text)
    if not t:
        return []
    seen = set()
    out = []
    for flag in RISK_FLAGS_ORDER:
        if flag in seen:
            continue
        keywords = RISK_KEYWORDS.get(flag) or []
        for kw in keywords:
            if kw and kw.lower() in t:
                seen.add(flag)
                out.append(flag)
                break
    return out


def _build_risk_explanations(risk_flags):
    """基于命中的 risk_flags 生成 risk_explanations 列表，含 severity / priority；顺序与 risk_flags 一致。"""
    out = []
    for flag in risk_flags or []:
        m = RISK_EXPLANATIONS_MAP.get(flag)
        sp = RISK_SEVERITY_PRIORITY_MAP.get(flag) or {}
        entry = {
            "flag": flag,
            "title": (m.get("title") if m else None) or flag.replace("_", " ").title(),
            "explanation": (m.get("explanation") if m else None) or "",
            "severity": sp.get("severity") or "medium",
            "priority": sp.get("priority") or "medium",
        }
        out.append(entry)
    return out


def _build_recommended_actions(risk_flags):
    """收集各命中 flag 的 actions，按 priority 高→中→低排序后去重；无命中时返回默认建议。"""
    if not risk_flags:
        return list(DEFAULT_ACTIONS_WHEN_NO_RISK)
    items = []
    for flag in risk_flags:
        sp = RISK_SEVERITY_PRIORITY_MAP.get(flag) or {}
        p = sp.get("priority") or "medium"
        rank = PRIORITY_ORDER.index(p) if p in PRIORITY_ORDER else 1
        for a in (RISK_EXPLANATIONS_MAP.get(flag) or {}).get("actions") or []:
            a = (a or "").strip()
            if a:
                items.append((rank, a))
    items.sort(key=lambda x: x[0])
    seen = set()
    out = []
    for _, a in items:
        if a not in seen:
            seen.add(a)
            out.append(a)
    return out if out else list(DEFAULT_ACTIONS_WHEN_NO_RISK)


def _build_overall_risk_level(risk_flags):
    """根据命中 flags 的 severity 生成 overall_risk_level：任一 high->high，否则任一 medium->medium，否则任一 low->low，否则 none。"""
    if not risk_flags:
        return "none"
    severities = set()
    for flag in risk_flags:
        s = (RISK_SEVERITY_PRIORITY_MAP.get(flag) or {}).get("severity") or "medium"
        severities.add(s)
    if "high" in severities:
        return "high"
    if "medium" in severities:
        return "medium"
    if "low" in severities:
        return "low"
    return "none"


def _build_grouped_risks(risk_explanations):
    """按 severity 分组为 high / medium / low；无命中时返回空结构。"""
    out = {"high": [], "medium": [], "low": []}
    for e in risk_explanations or []:
        s = (e.get("severity") or "medium").lower()
        if s not in out:
            out["medium"].append(e)
            continue
        out[s].append(e)
    return out


def _build_grouped_actions(risk_flags):
    """按 priority 将推荐动作分到 high_priority / medium_priority / low_priority；去重、稳定顺序。无命中时默认动作放 medium_priority。"""
    out = {"high_priority": [], "medium_priority": [], "low_priority": []}
    if not risk_flags:
        out["medium_priority"] = list(DEFAULT_ACTIONS_WHEN_NO_RISK)
        return out
    key_order = ("high_priority", "medium_priority", "low_priority")
    rank_to_key = {0: "high_priority", 1: "medium_priority", 2: "low_priority"}
    items = []
    for flag in risk_flags:
        sp = RISK_SEVERITY_PRIORITY_MAP.get(flag) or {}
        p = sp.get("priority") or "medium"
        rank = PRIORITY_ORDER.index(p) if p in PRIORITY_ORDER else 1
        for a in (RISK_EXPLANATIONS_MAP.get(flag) or {}).get("actions") or []:
            a = (a or "").strip()
            if a:
                items.append((rank, a))
    items.sort(key=lambda x: x[0])
    seen = set()
    for rank, a in items:
        if a in seen:
            continue
        seen.add(a)
        out[rank_to_key[rank]].append(a)
    return out


def _build_risk_summary(risk_flags, risk_explanations=None):
    """根据 risk_flags 与 grouped 严重度生成一句 risk_summary；可轻量呼应分组数量。无命中时返回默认句。"""
    if not risk_flags:
        return "No obvious baseline contract or dispute risk flags were detected."
    explanations = risk_explanations or _build_risk_explanations(risk_flags)
    n_high = sum(1 for e in explanations if (e.get("severity") or "").lower() == "high")
    n_medium = sum(1 for e in explanations if (e.get("severity") or "").lower() == "medium")
    n_low = sum(1 for e in explanations if (e.get("severity") or "").lower() == "low")
    readable = [FLAG_TO_READABLE.get(f, f.replace("_", " ")) for f in risk_flags]
    parts = []
    if n_high > 0:
        parts.append(f"{'one' if n_high == 1 else n_high} high-priority concern{'s' if n_high != 1 else ''}")
    if n_medium > 0:
        parts.append(f"{'one' if n_medium == 1 else n_medium} medium-level concern{'s' if n_medium != 1 else ''}")
    if n_low > 0:
        parts.append(f"{'one' if n_low == 1 else n_low} low-level concern{'s' if n_low != 1 else ''}")
    if len(parts) >= 2:
        return "This text raises " + " and ".join(parts) + "."
    if n_high == 1 and not n_medium and not n_low:
        return f"This text raises a high-priority concern around {readable[0]}."
    if n_low >= 1 and not n_high and not n_medium:
        return f"Only a low-level concern around {readable[0]} was detected." if len(readable) == 1 else f"This text raises low-level concerns around {', '.join(readable[:2])}{' and more' if len(readable) > 2 else ''}."
    if len(readable) == 1:
        return f"This text raises a medium-level concern around {readable[0]}."
    if len(readable) == 2:
        return f"This text mainly raises medium-level concerns around {readable[0]} and {readable[1]}."
    return f"This text raises medium-level concerns around {', '.join(readable[:-1])}, and {readable[-1]}."


def build_contract_risk_result(
    input_text=None,
    input_type="text",
    risk_flags=None,
    risk_summary=None,
    recommended_actions=None,
):
    """
    Module3 标准结果骨架。与 Module5 API-ready 风格兼容，缺数据时安全返回。
    后续可在此骨架内接入 contract_risk 等逻辑。

    输入:
      input_text: 用户输入的合同/纠纷相关文本或问题（可选）
      input_type: "question" | "text" | "document_excerpt"（概览用）
      risk_flags: 风险标签列表，默认 []
      risk_summary: 一句话风险摘要，默认 ""
      recommended_actions: 行动建议列表，默认 []

    输出: 标准 result dict（含 risk_explanations.severity/priority、overall_risk_level、risk_summary、recommended_actions 按优先级排序）
    当 risk_flags 未传入且有 input_text 时，自动识别 risk_flags，并生成 risk_explanations、risk_summary、recommended_actions。
    """
    recommended_actions_raw = recommended_actions

    raw = (input_text or "").strip()
    has_input = bool(raw)
    status = "ok" if has_input else "empty"
    message = "Contract risk result generated." if has_input else "No input provided; returning baseline structure."

    if risk_flags is None and has_input:
        risk_flags = _detect_risk_flags(raw)
    elif risk_flags is None:
        risk_flags = []
    else:
        risk_flags = list(risk_flags)

    risk_explanations = _build_risk_explanations(risk_flags)
    overall_risk_level = _build_overall_risk_level(risk_flags)
    grouped_risks = _build_grouped_risks(risk_explanations)
    grouped_actions = _build_grouped_actions(risk_flags)

    if risk_summary is None or (isinstance(risk_summary, str) and not risk_summary.strip()):
        risk_summary = _build_risk_summary(risk_flags, risk_explanations)
    else:
        risk_summary = str(risk_summary)

    if recommended_actions is None or (isinstance(recommended_actions, list) and len(recommended_actions) == 0):
        recommended_actions = _build_recommended_actions(risk_flags)
    else:
        recommended_actions = list(recommended_actions)

    now = datetime.now()
    metadata = {
        "module_name": "Module3",
        "version": MODULE3_VERSION,
        "generated_at": now.isoformat() if hasattr(now, "isoformat") else str(now),
    }
    text_len = len(raw)
    input_summary = {
        "input_type": input_type if input_type in ("question", "text", "document_excerpt") else "text",
        "text_length": text_len,
        "length": text_len,
        "preview": (raw[:80] + "..." if text_len > 80 else raw) if raw else None,
    }

    return {
        "status": status,
        "message": message,
        "metadata": metadata,
        "input_summary": input_summary,
        "risk_flags": risk_flags,
        "risk_explanations": risk_explanations,
        "grouped_risks": grouped_risks,
        "overall_risk_level": overall_risk_level,
        "risk_summary": risk_summary,
        "recommended_actions": recommended_actions,
        "grouped_actions": grouped_actions,
    }


def demo_module3_contract_risk_result():
    """
    演示 Phase1-A4：风险标签、分组(grouped_risks/grouped_actions)、risk_summary。
    覆盖：eviction(high)、deposit+repair(medium)、fee_charge(low)、无命中(none)。
    """
    cases = [
        ("eviction_risk -> high", "The landlord sent a section 21 notice and I might face eviction."),
        ("deposit + repair -> medium", "The deposit was not protected and the boiler is broken with mould."),
        ("fee_charge_risk -> low", "They charged an admin fee and a check-out fee."),
        ("no risk -> none", "The flat is nice and the area is quiet."),
    ]
    for label, text in cases:
        result = build_contract_risk_result(input_text=text, input_type="text")
        print(f"--- {label} ---")
        print("  risk_flags:", result.get("risk_flags"))
        print("  overall_risk_level:", result.get("overall_risk_level"))
        print("  risk_summary:", result.get("risk_summary"))
        print("  grouped_risks keys:", {k: len(v) for k, v in result.get("grouped_risks", {}).items()})
        print("  grouped_actions keys:", {k: len(v) for k, v in result.get("grouped_actions", {}).items()})
        print("  recommended_actions (first 3):", (result.get("recommended_actions") or [])[:3])
    print("--- Module3 Phase1-A4 demo 结束 ---")
    return result


if __name__ == "__main__":
    demo_module3_contract_risk_result()
