"""
Phase B3：risk_type → 法律/规则解释映射（非正式法律意见，供产品展示与后续扩展）。
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

# --- risk_type 映射逻辑：每类一条通用「法律语境」与双方视角说明 ---

LEGAL_RISK_GUIDANCE: dict[str, dict[str, str]] = {
    "deposit": {
        "legal_context": "押金条款通常应写明金额、托管/保护安排、退还条件、可扣款事由及争议处理；英国等地普遍要求押金进入法定保护计划。",
        "tenant_friendly_interpretation": "若押金不可退、扣款条件过宽或未约定保护机制，租客资金风险与举证负担会明显上升。",
        "landlord_friendly_interpretation": "房东通常希望押金覆盖损坏、欠租与违约成本，但扣款须有依据且程序合法，否则易引发纠纷。",
        "caution_note": "若未写明退还流程、扣款清单或保护计划，签约前应要求书面补充并保留支付凭证。",
    },
    "rent_increase": {
        "legal_context": "涨租条款一般应约定触发条件、频率、上限或参考标准、通知方式与协商程序；单方随时涨租在多数场景下对租客不利。",
        "tenant_friendly_interpretation": "模糊或单方主导的涨租表述会削弱租金可预期性，增加长期成本不确定性。",
        "landlord_friendly_interpretation": "房东通常希望保留与市场挂钩的调整空间，但条款仍应清晰以免被认定不公平。",
        "caution_note": "对「随时」「合理」等泛化措辞要特别警惕，建议明确通知期与上限或参考指数。",
    },
    "repairs": {
        "legal_context": "维修与维护责任应区分结构、设施、日常损耗与租客过失；将「全部维修」无限转嫁给租客通常风险较高。",
        "tenant_friendly_interpretation": "若租客承担范围过大，可能承担本应由房东或保险覆盖的结构性、系统性维修成本。",
        "landlord_friendly_interpretation": "房东通常希望租客承担合理使用范围内的损坏，但重大维修与合规义务仍多由房东承担。",
        "caution_note": "建议用附件或清单明确双方责任边界，避免「一切维修」类概括性表述。",
    },
    "termination": {
        "legal_context": "提前解约、break clause、违约金与通知期应相互衔接；单方过强终止权或过高惩罚性费用可能引发争议。",
        "tenant_friendly_interpretation": "若提前解约费用宽泛或违约金过高，实际退出成本可能远高于预期。",
        "landlord_friendly_interpretation": "房东通常希望保障稳定租金与交接成本，但罚金需与损失相称，避免被认定惩罚性条款。",
        "caution_note": "对 break clause、通知与押金结算的衔接条款应逐条核对，必要时寻求独立法律意见。",
    },
    "fees": {
        "legal_context": "额外收费应在合同中明确项目、金额或计算方式、触发条件与是否可退；不透明费用会抬高实际租赁成本。",
        "tenant_friendly_interpretation": "若存在大量笼统收费、强制清洁费或模糊管理费，实际支出可能显著高于 advertised 租金。",
        "landlord_friendly_interpretation": "房东或中介可约定合理费用，但重复收费与未披露收费易引发投诉与监管关注。",
        "caution_note": "要求对方提供费用清单与发票规则，拒绝未列明或口头新增收费。",
    },
    "notice": {
        "legal_context": "通知条款应写明期限长度、起算点、书面形式、送达地址与生效条件；偏袒一方或时间不明易导致程序与实体争议。",
        "tenant_friendly_interpretation": "若通知期过短或送达方式对租客不利，退租与抗辩空间可能被压缩。",
        "landlord_friendly_interpretation": "房东通常希望通知与送达方式可执行，以便及时收回房屋与处理欠租。",
        "caution_note": "若未写明通知期或书面要求，建议在签约前补充并确认与解约、押金条款一致。",
    },
}

# risk_type → 中文摘要用词（用于 summary_note）
RISK_TOPIC_LABELS: dict[str, str] = {
    "deposit": "押金",
    "rent_increase": "涨租",
    "repairs": "维修责任",
    "termination": "提前解约/终止",
    "fees": "额外收费",
    "notice": "通知期",
}


def enrich_risk_with_legal_context(risk_item: dict[str, Any]) -> dict[str, Any]:
    """
    enrich 流程：在 B2 风险结果上合并 legal_context 等字段；未知 risk_type 时填占位说明。
    """
    out = deepcopy(risk_item)
    rt = out.get("risk_type")
    if not isinstance(rt, str):
        return out

    guide = LEGAL_RISK_GUIDANCE.get(rt)
    if not guide:
        out["legal_context"] = "该风险类型暂无预设法律说明映射，建议人工复核。"
        out["tenant_friendly_interpretation"] = "请结合全文与适用法律判断对租客的影响。"
        out["landlord_friendly_interpretation"] = "请结合全文判断对房东权利义务的影响。"
        out["caution_note"] = "建议对未映射类型条款单独审查。"
        return out

    out["legal_context"] = guide["legal_context"]
    out["tenant_friendly_interpretation"] = guide["tenant_friendly_interpretation"]
    out["landlord_friendly_interpretation"] = guide["landlord_friendly_interpretation"]
    out["caution_note"] = guide["caution_note"]
    return out


def build_summary_note(detected_risks: list[dict[str, Any]]) -> str:
    """
    summary_note 生成逻辑：按出现过的 risk_type 频次取前若干类，拼一句可读摘要。
    """
    if not detected_risks:
        return "当前文本未匹配到预设风险主题，仍建议通读全文并结合当地法律评估。"

    from collections import Counter

    types = [r.get("risk_type") for r in detected_risks if isinstance(r.get("risk_type"), str)]
    if not types:
        return "已识别风险条目，但缺少 risk_type 字段，请检查分析结果。"

    top = [t for t, _ in Counter(types).most_common(4)]
    labels = "、".join(RISK_TOPIC_LABELS.get(t, t) for t in top)

    return (
        f"当前合同识别到的风险主题主要包括：{labels}。"
        "建议重点核对押金退还与保护、维修责任划分、涨租与解约条件、额外收费及通知程序，并结合适用法律判断。"
    )
