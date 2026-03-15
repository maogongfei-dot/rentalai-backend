# Module Transition 1: Module3 合同与纠纷风险系统 — 启动准备（骨架与标准结果）
#
# 第一阶段目标（仅风险骨架，不做复杂法律判断）:
#   - 输入: 租房合同/纠纷相关文本或问题
#   - 输出: 基础风险分类、风险摘要、建议下一步动作
#   - 保留未来扩展到更细合同条款分析的空间

from datetime import datetime

from routing_metadata import build_routing_metadata

# Phase4-2/4-3/4-4/4-Final、Phase5-1/5-2：文档条款切分、风险条款识别、重点条款摘要、文档分析块、缺失条款检测、弱条款检测（按需导入，避免循环依赖）
try:
    from clause_locator import build_clause_blocks
    from risk_clause_detector import detect_risk_clauses
    from highlighted_clause_builder import build_highlighted_clauses
    from document_analysis_builder import build_document_analysis_block
    from missing_clause_detector import detect_missing_clauses
    from weak_clause_detector import detect_weak_clauses
except ImportError:
    build_clause_blocks = None
    detect_risk_clauses = None
    build_highlighted_clauses = None
    build_document_analysis_block = None
    detect_missing_clauses = None
    detect_weak_clauses = None

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
        "rent review", "increase rent", "increase the rent", "涨租", "加租",
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


# ---------- Phase1 Final: 统一 Module3 最终输出结构 ----------
MODULE3_RESULT_KEYS = (
    "input_type",
    "scenario",
    "risk_flags",
    "severity",
    "explanation",
    "recommended_actions",
    "action_details",
    "ordered_action_details",
    "law_topics",
    "legal_references",
    "legal_reasoning",
    "legal_summary",
    "evidence_required",
    "recommended_steps",
    "possible_outcomes",
    "scenario_block",  # Phase3 Final: 场景闭环统一结构
    # Phase4：文档条款与风险条款（由 build_contract_risk_result_from_document 填充）
    # "clause_blocks",
    # "risk_clauses",
    # "risk_clause_count",
)

# Phase2-1: 基于风险标记 / 输入类型 / 场景的法律主题映射（与需求一一对应，含别名以兼容后续扩展）
LAW_TOPIC_FLAG_MAP = {
    "deposit_risk": ["deposit_protection"],
    "deposit_dispute": ["deposit_protection"],
    "rent_increase_risk": ["rent_increase"],
    "rent_increase_clause": ["rent_increase"],
    "termination_risk": ["termination_notice"],
    "notice_risk": ["termination_notice"],
    "eviction_risk": ["termination_notice"],
    "repair_risk": ["repair_obligation"],
    "repair_issue": ["repair_obligation"],
    "fee_charge_risk": ["prohibited_fees"],
    "fee_issue": ["prohibited_fees"],
    "illegal_fee": ["prohibited_fees"],
    "unfair_clause": ["unfair_terms"],
}


def get_law_topics(risk_flags, input_type: str = "", scenario: str = "") -> list:
    """
    Phase2-1：根据 risk_flags / input_type / scenario 生成基础法律主题列表（law_topics）。
    - 优先基于已知 risk flag 映射到主题；
    - 若存在不公平条款类 flag（unfair_clause / *_unfair），补充 unfair_terms；
    - 若没有任何主题且为合同条款审查场景（contract_review_path 或 input_type=contract_clause），补充 unfair_terms。
    """
    topics = []
    seen = set()
    flags = list(risk_flags or [])

    # 1) flag -> 主题映射
    for flag in flags:
        for t in LAW_TOPIC_FLAG_MAP.get(flag, []) or []:
            if t not in seen:
                seen.add(t)
                topics.append(t)

    # 2) 不公平条款类 flag -> unfair_terms
    if any(
        isinstance(f, str)
        and (f == "unfair_clause" or f.endswith("_unfair"))
        for f in flags
    ):
        if "unfair_terms" not in seen:
            seen.add("unfair_terms")
            topics.append("unfair_terms")

    # 3) 场景兜底：合同条款审查但未命中具体主题时，给一个 unfair_terms 主题
    if not topics and (
        scenario == "contract_review_path" or (input_type or "") == "contract_clause"
    ):
        if "unfair_terms" not in seen:
            seen.add("unfair_terms")
            topics.append("unfair_terms")

    return topics


# Phase3-1: 根据 risk_flags / law_topics / input_type 识别具体租房场景（优先级：先匹配先返回）
def detect_scenario(risk_flags, law_topics, input_type: str = "") -> str:
    """
    根据当前风险标记、法律主题和输入类型识别具体租房场景，供证据-动作-结果闭环使用。
    无法明确识别时返回 general_rental_issue。
    """
    flags = set(f for f in (risk_flags or []) if isinstance(f, str))
    topics = set(t for t in (law_topics or []) if isinstance(t, str))

    if "deposit_risk" in flags or "deposit_dispute" in flags or "deposit_protection" in topics:
        return "deposit_dispute"
    if "rent_increase_risk" in flags or "rent_increase" in topics:
        return "rent_increase"
    if "notice_risk" in flags or "eviction_risk" in flags or "termination_risk" in flags or "termination_notice" in topics:
        return "termination_exit"
    if "repair_risk" in flags or "repair_issue" in flags or "repair_obligation" in topics:
        return "repair_issue"
    if "fee_charge_risk" in flags or "fee_issue" in flags or "illegal_fee" in flags or "prohibited_fees" in topics:
        return "fee_issue"
    if "unfair_clause" in flags or "unfair_terms" in topics:
        return "unfair_contract_clause"
    return "general_rental_issue"


# Phase3-2: scenario -> 建议准备的证据清单
EVIDENCE_REQUIRED_MAP = {
    "deposit_dispute": [
        "tenancy agreement",
        "deposit payment record",
        "deposit protection information",
        "move-in and move-out photos",
        "chat or email history",
    ],
    "rent_increase": [
        "tenancy agreement",
        "rent clause",
        "rent increase notice",
        "payment history",
        "chat or email history",
    ],
    "termination_exit": [
        "tenancy agreement",
        "break clause or termination clause",
        "notice emails or messages",
        "move-out timeline",
        "payment history",
    ],
    "repair_issue": [
        "tenancy agreement",
        "repair messages or emails",
        "photos or videos of the issue",
        "inspection records",
        "timeline notes",
    ],
    "unfair_contract_clause": [
        "tenancy agreement",
        "exact contract clause text",
        "related messages or emails",
    ],
    "fee_issue": [
        "tenancy agreement",
        "fee request or invoice",
        "payment record",
        "chat or email history",
    ],
    "general_rental_issue": [
        "tenancy agreement",
        "chat or email history",
        "payment record",
        "related photos or files",
    ],
}


def get_evidence_required(scenario: str) -> list:
    """Phase3-2：根据 scenario 返回建议准备的证据清单。"""
    return list(EVIDENCE_REQUIRED_MAP.get(scenario, EVIDENCE_REQUIRED_MAP["general_rental_issue"]))


# Phase3-3: scenario -> 建议处理步骤（动作层，适合前端展示）
RECOMMENDED_STEPS_MAP = {
    "deposit_dispute": [
        "确认押金是否已进入保护机制。",
        "整理合同、押金付款记录、入住和退房证据。",
        "明确房东或中介扣款/拒退押金的理由。",
        "准备正式沟通，必要时继续追讨或升级处理。",
    ],
    "rent_increase": [
        "先查看合同中的涨租条款。",
        "确认当前是否仍处于固定租期或其他租期状态。",
        "核对通知方式、通知时间和涨租条件。",
        "再决定是否需要回应、协商或进一步处理。",
    ],
    "termination_exit": [
        "查看合同中的解约条款、break clause 或 notice 条款。",
        "整理已经发送或收到的通知记录。",
        "确认当前租期状态、搬离时间和付款情况。",
        "准备正式沟通，避免因流程不清导致额外争议。",
    ],
    "repair_issue": [
        "整理问题照片、视频和报修记录。",
        "确认合同中关于维修责任的约定。",
        "保存催修沟通记录和时间线。",
        "如问题持续未解决，再考虑升级处理。",
    ],
    "unfair_contract_clause": [
        "标出需要重点审查的合同条款。",
        "分析条款是否存在明显失衡、模糊或偏向单方。",
        "结合合同上下文一起理解该条款。",
        "如有必要，要求对方解释、修改或重新确认。",
    ],
    "fee_issue": [
        "核对收费项目名称和金额。",
        "查看合同中是否有明确收费依据。",
        "保存付款记录、收费通知和相关沟通记录。",
        "如收费不清晰或不合理，要求说明或拒绝不当收费。",
    ],
    "general_rental_issue": [
        "先整理合同、付款记录和沟通记录。",
        "明确当前问题的核心争议点。",
        "确认问题更接近合同、押金、维修还是收费场景。",
        "再决定下一步处理方向。",
    ],
}


def get_recommended_steps(scenario: str) -> list:
    """Phase3-3：根据 scenario 返回建议处理步骤（动作层）。"""
    return list(RECOMMENDED_STEPS_MAP.get(scenario, RECOMMENDED_STEPS_MAP["general_rental_issue"]))


# Phase3-4: scenario -> 可能结果（补完证据-动作-结果闭环）
POSSIBLE_OUTCOMES_MAP = {
    "deposit_dispute": [
        "房东或中介说明扣款理由。",
        "部分押金被退回。",
        "全部押金被退回。",
        "争议继续升级，需要进入进一步处理流程。",
    ],
    "rent_increase": [
        "租客接受涨租安排。",
        "双方进入协商。",
        "涨租依据被质疑或需要进一步解释。",
        "租约后续安排需要重新决定。",
    ],
    "termination_exit": [
        "双方就解约或搬离安排达成一致。",
        "围绕通知、租金或责任产生争议。",
        "可能出现额外付款或责任风险。",
        "搬离流程最终被确认。",
    ],
    "repair_issue": [
        "维修问题得到处理。",
        "维修继续拖延。",
        "问题升级为正式投诉或进一步争议。",
        "证据和时间线变得更加重要。",
    ],
    "unfair_contract_clause": [
        "条款得到解释。",
        "条款被修改或重新确认。",
        "条款公平性继续受到质疑。",
        "签约风险仍然存在。",
    ],
    "fee_issue": [
        "收费项目被解释清楚。",
        "收费被撤回或调整。",
        "收费问题进入争议状态。",
        "可能需要进一步投诉或处理。",
    ],
    "general_rental_issue": [
        "问题逐渐被澄清。",
        "仍需补充更多证据。",
        "双方开始协商。",
        "后续可能需要升级处理。",
    ],
}


def get_possible_outcomes(scenario: str) -> list:
    """Phase3-4：根据 scenario 返回可能结果列表。"""
    return list(POSSIBLE_OUTCOMES_MAP.get(scenario, POSSIBLE_OUTCOMES_MAP["general_rental_issue"]))


# Phase3 Final: 场景闭环统一结构（证据-动作-结果）
def build_scenario_block(
    scenario: str,
    evidence_required: list,
    recommended_steps: list,
    possible_outcomes: list,
) -> dict:
    """
    将 Phase3 场景闭环四要素整理为稳定结构，供下游 Phase4 等使用。
    返回: { scenario, evidence_required, recommended_steps, possible_outcomes }
    """
    return {
        "scenario": scenario or "",
        "evidence_required": list(evidence_required) if evidence_required is not None else [],
        "recommended_steps": list(recommended_steps) if recommended_steps is not None else [],
        "possible_outcomes": list(possible_outcomes) if possible_outcomes is not None else [],
    }


# Phase2-2: law_topic -> legal_reference (source) 与 legal_reasoning 文案
LEGAL_REFERENCE_REASONING_MAP = {
    "deposit_protection": {
        "source": "Housing Act 2004 / tenancy deposit protection rules",
        "reasoning": "该问题涉及押金是否依法受到保护，以及押金处理规则。",
    },
    "rent_increase": {
        "source": "tenancy rent increase rules / contract fairness considerations",
        "reasoning": "该问题涉及房租调整条件、通知方式以及条款公平性。",
    },
    "termination_notice": {
        "source": "tenancy notice / possession notice related rules",
        "reasoning": "该问题涉及租约终止、通知要求或收回房屋流程。",
    },
    "repair_obligation": {
        "source": "landlord repair obligations",
        "reasoning": "该问题涉及房东与租客之间的维修责任分配。",
    },
    "prohibited_fees": {
        "source": "Tenant Fees Act 2019",
        "reasoning": "该问题涉及租房过程中的不合理收费或被禁止的收费项目。",
    },
    "unfair_terms": {
        "source": "contract fairness / unfair terms principles",
        "reasoning": "该问题涉及合同条款是否存在明显失衡、不清晰或偏向单方。",
    },
}


def get_legal_references(law_topics):
    """
    Phase2-2：根据 law_topics 生成 legal_references 与 legal_reasoning，按 topic 去重。
    返回 (list[dict], list[str])，分别对应 legal_references 与 legal_reasoning。
    """
    refs = []
    reasoning_list = []
    seen = set()
    for topic in law_topics or []:
        if not isinstance(topic, str) or topic in seen:
            continue
        seen.add(topic)
        entry = LEGAL_REFERENCE_REASONING_MAP.get(topic)
        if not entry:
            continue
        refs.append({"topic": topic, "source": entry.get("source") or ""})
        r = entry.get("reasoning")
        if r:
            reasoning_list.append(r)
    return refs, reasoning_list


def build_legal_summary(
    explanation: str,
    law_topics,
    legal_references,
    legal_reasoning,
) -> str:
    """
    Phase2-3：将 explanation、law_topics、legal_references、legal_reasoning 组合成一段易读的 legal_summary。
    先说明涉及的法律主题，再说明为什么相关，最后说明参考依据；多主题时简单合并，保持简洁。
    """
    explanation = (explanation or "").strip()
    topics = [t for t in (law_topics or []) if isinstance(t, str) and t.strip()]
    refs = [r for r in (legal_references or []) if isinstance(r, dict) and r.get("topic")]
    reasons = [r for r in (legal_reasoning or []) if isinstance(r, str) and r.strip()]

    if not topics and not refs:
        return explanation or "当前未识别到明确的法律主题；可根据具体条款或纠纷再细化。"

    parts = []
    # 1) 涉及什么法律主题
    if topics:
        if len(topics) == 1:
            parts.append(f"本问题主要涉及与「{topics[0]}」相关的法律主题。")
        else:
            parts.append(f"本问题主要涉及「{'」「'.join(topics)}」等法律主题。")
    # 2) 为什么相关（结合 legal_reasoning）
    if reasons:
        if len(reasons) == 1:
            parts.append(reasons[0])
        else:
            parts.append("具体而言，" + "；".join(reasons))
    # 3) 参考依据（结合 legal_references）
    if refs:
        sources = [r.get("source") or "" for r in refs if r.get("source")]
        if sources:
            parts.append("参考依据包括：" + "；".join(sources) + "。")

    return " ".join(parts) if parts else (explanation or "")


def build_module3_result(
    input_type="",
    scenario="",
    risk_flags=None,
    severity="",
    explanation="",
    recommended_actions=None,
    action_details=None,
    ordered_action_details=None,
    law_topics=None,
    legal_references=None,
    legal_reasoning=None,
    legal_summary=None,
    evidence_required=None,
    recommended_steps=None,
    possible_outcomes=None,
):
    """
    Phase1 Final：统一 Module3 的最终输出结构。
    将输入类型、场景、风险标记、严重度、解释、推荐行动、法律主题、法律依据、legal_summary、evidence_required、recommended_steps、possible_outcomes 整理为固定字段的 result。
    """
    return {
        "input_type": input_type or "",
        "scenario": scenario or "",
        "risk_flags": list(risk_flags) if risk_flags is not None else [],
        "severity": severity or "",
        "explanation": explanation or "",
        "recommended_actions": list(recommended_actions) if recommended_actions is not None else [],
        "action_details": list(action_details) if action_details is not None else [],
        "ordered_action_details": list(ordered_action_details) if ordered_action_details is not None else [],
        "law_topics": list(law_topics) if law_topics is not None else [],
        "legal_references": list(legal_references) if legal_references is not None else [],
        "legal_reasoning": list(legal_reasoning) if legal_reasoning is not None else [],
        "legal_summary": (legal_summary or "").strip() if legal_summary is not None else "",
        "evidence_required": list(evidence_required) if evidence_required is not None else [],
        "recommended_steps": list(recommended_steps) if recommended_steps is not None else [],
        "possible_outcomes": list(possible_outcomes) if possible_outcomes is not None else [],
    }


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

    # Phase1-A5-7: 统一路由元数据生成，一次调用得到 input_type / analysis_mode / response_focus / guided_summary / recommended_path / next_step_hint
    routing = build_routing_metadata(raw)
    detected_input_type = routing["input_type"]
    analysis_mode = routing["analysis_mode"]
    response_focus = routing["response_focus"]
    guided_summary = routing["guided_summary"]
    recommended_path = routing["recommended_path"]
    next_step_hint = routing["next_step_hint"]
    # Phase1-A6-1: recommended_actions 由 routing 提供（基于 recommended_path 的基础动作建议）
    recommended_actions = routing["recommended_actions"]
    # Phase1-A6-2: action_details 为 recommended_actions 的中文可展示版
    action_details = routing["action_details"]
    # Phase1-A6-3: 动作优先级映射与按优先级排序的可展示列表
    action_priority_map = routing["action_priority_map"]
    ordered_action_details = routing["ordered_action_details"]

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

    now = datetime.now()
    metadata = {
        "module_name": "Module3",
        "version": MODULE3_VERSION,
        "generated_at": now.isoformat() if hasattr(now, "isoformat") else str(now),
    }
    text_len = len(raw)
    input_summary = {
        "input_type": detected_input_type,
        "text_length": text_len,
        "length": text_len,
        "preview": (raw[:80] + "..." if text_len > 80 else raw) if raw else None,
    }

    # Phase1 Final: 统一写入标准 result 结构
    # Phase2-1: 基于风险与路径生成法律主题 law_topics（此处仍用 recommended_path 作 fallback）
    law_topics = get_law_topics(risk_flags, detected_input_type, recommended_path)
    # Phase3-1: 根据 risk_flags / law_topics / input_type 识别具体租房场景
    scenario = detect_scenario(risk_flags, law_topics, detected_input_type)
    # Phase3-2: 根据 scenario 生成证据清单
    evidence_required = get_evidence_required(scenario)
    # Phase3-3: 根据 scenario 生成建议处理步骤
    recommended_steps = get_recommended_steps(scenario)
    # Phase3-4: 根据 scenario 生成可能结果
    possible_outcomes = get_possible_outcomes(scenario)
    # Phase3 Final: 场景闭环统一收口
    scenario_block = build_scenario_block(scenario, evidence_required, recommended_steps, possible_outcomes)
    # Phase2-2: 根据 law_topics 生成 legal_references 与 legal_reasoning
    legal_references, legal_reasoning = get_legal_references(law_topics)
    # Phase2-3: 组合成易读的 legal_summary
    legal_summary = build_legal_summary(risk_summary, law_topics, legal_references, legal_reasoning)
    unified_result = build_module3_result(
        input_type=detected_input_type,
        scenario=scenario,
        risk_flags=risk_flags,
        severity=overall_risk_level,
        explanation=risk_summary,
        recommended_actions=recommended_actions,
        action_details=action_details,
        ordered_action_details=ordered_action_details,
        law_topics=law_topics,
        legal_references=legal_references,
        legal_reasoning=legal_reasoning,
        legal_summary=legal_summary,
        evidence_required=evidence_required,
        recommended_steps=recommended_steps,
        possible_outcomes=possible_outcomes,
    )

    # 返回统一 result 与兼容字段；scenario_block 为 Phase3 场景闭环统一结构
    return {
        **unified_result,
        "scenario_block": scenario_block,
        "status": status,
        "message": message,
        "metadata": metadata,
        "input_summary": input_summary,
        "analysis_mode": analysis_mode,
        "response_focus": response_focus,
        "guided_summary": guided_summary,
        "recommended_path": recommended_path,
        "next_step_hint": next_step_hint,
        "risk_explanations": risk_explanations,
        "grouped_risks": grouped_risks,
        "overall_risk_level": overall_risk_level,
        "risk_summary": risk_summary,
        "action_priority_map": action_priority_map,
        "grouped_actions": grouped_actions,
    }


def build_contract_risk_result_from_document(document_data: dict) -> dict:
    """
    Phase4：基于文档读取结果生成 Module3 风格 result，并附加文档分析块（document_analysis_block）及扁平字段 clause_blocks、risk_clauses、highlighted_clauses 等。
    输入为 read_document() 的返回值；文档分析逻辑收口于 build_document_analysis_block，再写入 result。
    """
    base = build_contract_risk_result(input_text=(document_data or {}).get("full_text") or "")
    doc = document_data or {}
    if build_clause_blocks is None or detect_risk_clauses is None:
        clause_blocks = []
        risk_clauses = []
        highlighted_clauses = []
        missing_clauses = []
        weak_clauses = []
    else:
        clause_blocks = build_clause_blocks(document_data)
        risk_clauses = detect_risk_clauses(clause_blocks)
        highlighted_clauses = (build_highlighted_clauses(risk_clauses, max_items=3) if build_highlighted_clauses else [])
        missing_clauses = (detect_missing_clauses(clause_blocks) if detect_missing_clauses else [])
        weak_clauses = (detect_weak_clauses(clause_blocks) if detect_weak_clauses else [])
    # Phase4 Final：统一文档分析输出块
    document_analysis_block = (
        build_document_analysis_block(doc, clause_blocks, risk_clauses, highlighted_clauses)
        if build_document_analysis_block
        else {
            "document_summary": {"file_name": doc.get("file_name") or "", "file_type": doc.get("file_type") or "", "block_count": 0, "risk_clause_count": 0, "highlighted_clause_count": 0},
            "clause_blocks": [],
            "risk_clauses": [],
            "highlighted_clauses": [],
        }
    )
    base["document_analysis_block"] = document_analysis_block
    # 保留原扁平字段，便于既有调用方使用；Phase5-1 缺失条款
    base["clause_blocks"] = clause_blocks
    base["risk_clauses"] = risk_clauses
    base["risk_clause_count"] = len(risk_clauses)
    base["highlighted_clauses"] = highlighted_clauses
    base["highlighted_clause_count"] = len(highlighted_clauses)
    base["missing_clauses"] = missing_clauses
    base["missing_clause_count"] = len(missing_clauses)
    base["weak_clauses"] = weak_clauses
    base["weak_clause_count"] = len(weak_clauses)
    return base


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
