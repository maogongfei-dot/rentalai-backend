"""
Phase B4：risk_type → 行动建议映射（checklist / 提问 / 证据），与 severity 解耦的 action_priority。
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

# --- 风险 → 行动建议映射逻辑：每类 checklist、向对方追问、需保留的证据 ---

RISK_ACTION_GUIDANCE: dict[str, dict[str, list[str]]] = {
    "deposit": {
        "action_checklist": [
            "确认押金金额、支付对象与到账方式",
            "要求书面列明全额退还条件与可扣款情形",
            "确认是否进入法定押金保护计划及证书信息",
            "保留押金转账记录与收据",
        ],
        "ask_landlord_questions": [
            "押金在什么条件下会全额退还？哪些情况可从押金扣款？",
            "押金是否已/将存入保护计划？能否提供相关编号或证明？",
        ],
        "supporting_evidence_needed": [
            "合同最终签字版",
            "押金支付银行流水或收据",
            "房东/中介关于押金条款的书面说明或邮件",
        ],
    },
    "rent_increase": {
        "action_checklist": [
            "确认涨租触发条件、频率与上限或参考标准",
            "确认提前通知期与通知形式（书面/邮件）",
            "确认是否可协商或申诉程序",
            "要求对模糊表述（如“合理涨租”）书面解释",
        ],
        "ask_landlord_questions": [
            "涨租前会提前多久书面通知？能否约定年度上限？",
            "租金复审具体依据什么（指数、市场价）？",
        ],
        "supporting_evidence_needed": [
            "含租金条款的合同页",
            "历史租金与通知往来记录",
            "当地租金指引或可比房源信息（如有）",
        ],
    },
    "repairs": {
        "action_checklist": [
            "要求附件或清单列明房东与租客维修范围",
            "区分结构/设施/花园/家电与日常损耗",
            "确认紧急维修联络方式与费用垫付规则",
            "对“租客承担全部维修”等表述要求修订或说明",
        ],
        "ask_landlord_questions": [
            "哪些维修必须由房东承担？哪些由租客承担？",
            "重大故障（漏水、供暖）由谁联系承包商与付费？",
        ],
        "supporting_evidence_needed": [
            "入住检查清单与照片",
            "报修与房东/物业沟通记录",
            "维修发票与付款凭证（如已发生）",
        ],
    },
    "termination": {
        "action_checklist": [
            "核对 break clause 是否适用自身租期与条件",
            "确认提前解约或违约金计算公式与上限",
            "确认通知方式、送达地址与通知期起算",
            "核对退租交接与押金结算时点",
        ],
        "ask_landlord_questions": [
            "提前解约需满足哪些条件？罚金是否与损失挂钩？",
            "通知应以何种方式送达才有效？",
        ],
        "supporting_evidence_needed": [
            "解约与通知相关合同条款页",
            "书面退租通知副本与送达证明",
            "往来邮件或消息记录",
        ],
    },
    "fees": {
        "action_checklist": [
            "要求列明全部额外收费项目及金额或计算方式",
            "确认每项收费的触发条件与是否可退",
            "拒绝未在合同中列明的口头或事后收费",
            "核对广告/报价与合同费用是否一致",
        ],
        "ask_landlord_questions": [
            "除租金外还有哪些必付费用？是否有行政费、清洁费？",
            "滞纳金或违约金如何计算？有无上限？",
        ],
        "supporting_evidence_needed": [
            "合同费用条款与附件",
            "广告/房源页面截图或报价单",
            "已支付费用的收据与转账记录",
        ],
    },
    "notice": {
        "action_checklist": [
            "确认各类通知的期限（月/周/日）与起算点",
            "确认是否必须书面及可接受的送达方式",
            "确认通知与解约、涨租、维修等条款是否衔接",
            "保存己方发出通知的副本与送达凭证",
        ],
        "ask_landlord_questions": [
            "退租或涨租通知需提前多久、以何种形式发出？",
            "通知寄至哪个地址才算有效？",
        ],
        "supporting_evidence_needed": [
            "载明通知期的合同条款",
            "已发送通知的邮件/挂号信回执或快递单号",
        ],
    },
}

# 用于 summary.next_step_summary：按类型一条短句，优先高风险项拼接
NEXT_STEP_LINE_BY_TYPE: dict[str, str] = {
    "deposit": "优先核对押金金额、退还条件与押金保护安排",
    "rent_increase": "确认涨租触发条件、通知期与是否可协商",
    "repairs": "要求明确房东与租客维修责任分工并保留入住记录",
    "termination": "核对提前解约、违约金与通知程序后再签字",
    "fees": "在签约前确认全部额外收费项目与触发条件",
    "notice": "确认各类通知的期限、形式与送达要求",
}


def get_action_priority(risk_item: dict[str, Any]) -> str:
    """
    action_priority 逻辑：默认与 severity 对齐；
    deposit / termination / rent_increase 且 severity 为 medium 时，行动优先级提升为 high。
    """
    sev = risk_item.get("severity") or "low"
    rt = risk_item.get("risk_type") or ""
    if sev == "high":
        return "high"
    if sev == "low":
        return "low"
    if sev == "medium" and rt in ("deposit", "termination", "rent_increase"):
        return "high"
    return "medium"


def enrich_risk_with_actions(risk_item: dict[str, Any]) -> dict[str, Any]:
    """合并行动建议字段；未知 risk_type 时给最小占位列表。"""
    out = deepcopy(risk_item)
    rt = out.get("risk_type")
    if not isinstance(rt, str):
        return out

    out["action_priority"] = get_action_priority(out)

    guide = RISK_ACTION_GUIDANCE.get(rt)
    if not guide:
        out["action_checklist"] = ["请根据合同全文人工列出待办事项"]
        out["ask_landlord_questions"] = ["请向对方书面确认该条款的具体含义与适用条件"]
        out["supporting_evidence_needed"] = ["合同文本", "往来沟通记录"]
        return out

    out["action_checklist"] = list(guide["action_checklist"])
    out["ask_landlord_questions"] = list(guide["ask_landlord_questions"])
    out["supporting_evidence_needed"] = list(guide["supporting_evidence_needed"])
    return out


def build_next_step_summary(detected: list[dict[str, Any]]) -> list[str]:
    """
    next_step_summary 生成逻辑：优先 high action_priority，其次按原顺序取类型对应短句，最多 3 条不重复。
    """
    if not detected:
        return [
            "通读合同全文并标注不明条款",
            "对关键事项要求对方书面答复",
            "保留签约前所有沟通与广告材料",
        ]

    ap_order = {"high": 3, "medium": 2, "low": 1}

    def sort_key(r: dict[str, Any]) -> tuple[int, int]:
        ap = r.get("action_priority") or get_action_priority(r)
        pri = ap_order.get(ap, 0)
        # 同优先级保持 stable：用 risk_type 顺序
        type_order = ["deposit", "rent_increase", "repairs", "termination", "fees", "notice"]
        idx = type_order.index(r["risk_type"]) if r.get("risk_type") in type_order else 99
        return (-pri, idx)

    ranked = sorted(detected, key=sort_key)
    lines: list[str] = []
    for r in ranked:
        rt = r.get("risk_type")
        if not isinstance(rt, str):
            continue
        line = NEXT_STEP_LINE_BY_TYPE.get(rt)
        if line and line not in lines:
            lines.append(line)
        if len(lines) >= 3:
            break

    if len(lines) < 3:
        fallback = "签约前对未列明事项要求书面补充并核对适用法律"
        if fallback not in lines:
            lines.append(fallback)
    return lines[:3]
