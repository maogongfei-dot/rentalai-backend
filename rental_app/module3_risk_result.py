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
    """基于命中的 risk_flags 生成 risk_explanations 列表，顺序与 risk_flags 一致。"""
    out = []
    for flag in risk_flags or []:
        m = RISK_EXPLANATIONS_MAP.get(flag)
        if not m:
            out.append({"flag": flag, "title": flag.replace("_", " ").title(), "explanation": ""})
            continue
        out.append({
            "flag": flag,
            "title": m.get("title") or flag.replace("_", " ").title(),
            "explanation": m.get("explanation") or "",
        })
    return out


def _build_recommended_actions(risk_flags):
    """收集各命中 flag 的默认 actions，去重、稳定顺序；无命中时返回默认建议。"""
    if not risk_flags:
        return list(DEFAULT_ACTIONS_WHEN_NO_RISK)
    seen = set()
    out = []
    for flag in risk_flags:
        m = RISK_EXPLANATIONS_MAP.get(flag)
        if not m:
            continue
        for a in m.get("actions") or []:
            a = (a or "").strip()
            if a and a not in seen:
                seen.add(a)
                out.append(a)
    return out if out else list(DEFAULT_ACTIONS_WHEN_NO_RISK)


def _build_risk_summary(risk_flags):
    """根据 risk_flags 生成一句自然语言 risk_summary；无命中时返回默认句。"""
    if not risk_flags:
        return "No obvious baseline contract or dispute risk flags were detected."
    readable = [FLAG_TO_READABLE.get(f, f.replace("_", " ")) for f in risk_flags]
    if len(readable) == 1:
        return f"This text mainly raises a {readable[0]}-related concern."
    if len(readable) == 2:
        return f"This text mainly raises {readable[0]} and {readable[1]} concerns."
    return f"This text raises multiple concerns, mainly around {', '.join(readable[:-1])}, and {readable[-1]}."


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

    输出: 标准 result dict（status, message, metadata, input_summary, risk_flags, risk_explanations, risk_summary, recommended_actions）
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

    if risk_summary is None or (isinstance(risk_summary, str) and not risk_summary.strip()):
        risk_summary = _build_risk_summary(risk_flags)
    else:
        risk_summary = str(risk_summary)

    risk_explanations = _build_risk_explanations(risk_flags)
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
        "risk_summary": risk_summary,
        "recommended_actions": recommended_actions,
    }


def demo_module3_contract_risk_result():
    """
    演示 Phase1-A2：风险标签、解释与推荐动作。
    覆盖示例：deposit+repair、notice+landlord entry、无风险关键词。
    """
    cases = [
        ("deposit + repair", "The deposit was not protected and the boiler is broken with mould in the bathroom."),
        ("notice + landlord entry", "They gave me two months notice and the landlord did an inspection without notice."),
        ("no risk keywords", "The flat is nice and the area is quiet."),
    ]
    for label, text in cases:
        result = build_contract_risk_result(input_text=text, input_type="text")
        print(f"--- {label} ---")
        print("  risk_flags:", result.get("risk_flags"))
        print("  risk_summary:", result.get("risk_summary"))
        print("  risk_explanations:", [(e.get("flag"), e.get("title")) for e in result.get("risk_explanations", [])])
        print("  recommended_actions:", result.get("recommended_actions"))
    print("--- Module3 Phase1-A2 demo 结束 ---")
    return result


if __name__ == "__main__":
    demo_module3_contract_risk_result()
