"""
Phase 3 合同分析：主分析入口（基础规则扫描 + 主题覆盖）。
"""

from __future__ import annotations

from typing import Any

from .contract_models import ContractInput
from .contract_rules import (
    detect_contract_topic_labels,
    evaluate_deposit_amount_risk,
    scan_text_keyword_risks,
    scan_topic_bad_pattern_risks,
    scan_topic_missing_items,
)


def _dedupe_risks(risks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for r in risks:
        rid = str(r.get("rule_id") or r.get("title") or "")
        if not rid or rid in seen:
            continue
        seen.add(rid)
        out.append(r)
    return out


def _normalize_analysis_output(data: dict[str, Any]) -> dict[str, Any]:
    """保证输出字段类型稳定：risks / missing_items / recommendations / detected_topics 均为 list。"""
    out = dict(data)
    raw_risks = out.get("risks")
    if not isinstance(raw_risks, list):
        raw_risks = []
    out["risks"] = [x for x in raw_risks if isinstance(x, dict)]
    for key in ("missing_items", "recommendations", "detected_topics"):
        v = out.get(key)
        if not isinstance(v, list):
            v = []
        else:
            v = [str(i).strip() for i in v if str(i).strip()]
        out[key] = v
    out["summary"] = str(out.get("summary") or "").strip()
    return out


def _missing_covers_notice_and_repair(missing_items: list[str]) -> bool:
    """用于针对性建议：同时缺失通知期与维修主题。"""
    has_n = any(("Notice" in m or "通知期" in m) for m in missing_items)
    has_r = any(("Repair" in m or "Maintenance" in m or "维修" in m) for m in missing_items)
    return has_n and has_r


def _uniq_preserve(xs: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for x in xs:
        t = (x or "").strip()
        if not t or t in seen:
            continue
        seen.add(t)
        out.append(t)
    return out


def detect_contract_topics(contract_text: str) -> list[str]:
    """返回合同中已识别到的主题标签列表（人类可读）。"""
    return detect_contract_topic_labels(contract_text)


def detect_contract_risks(contract_text: str, contract_input: ContractInput) -> list[dict[str, Any]]:
    """合并：数值押金风险 + Part1 全局关键词 + Part2 主题不合理表述。"""
    risks: list[dict[str, Any]] = []
    dep = evaluate_deposit_amount_risk(contract_input.deposit_amount, contract_input.monthly_rent)
    if dep is not None:
        risks.append(dep)
    risks.extend(scan_text_keyword_risks(contract_text))
    risks.extend(scan_topic_bad_pattern_risks(contract_text))
    return _dedupe_risks(risks)


def detect_missing_items(contract_text: str) -> list[str]:
    """未覆盖的主题列表（文案标签）。"""
    return scan_topic_missing_items(contract_text)


def build_contract_summary(
    risks: list[dict[str, Any]],
    missing_items: list[str],
    detected_topics: list[str],
) -> str:
    """生成摘要句，便于 UI / explain 展示。"""
    rc, mc, dc = len(risks), len(missing_items), len(detected_topics)
    if rc == 0 and mc == 0:
        return (
            f"已识别 {dc} 个常见主题关键词；未发现全局规则命中的风险项或明显主题缺失。"
            "仍请通读全文并自行核对事实与数字。"
        )
    parts = [
        f"共提示 {rc} 条风险项",
        f"正文约覆盖 {dc} 类常见主题",
        f"另有 {mc} 类主题未在文中匹配到关键词（可能未约定或写在附件）",
    ]
    return "；".join(parts) + "。"


def build_recommendations(
    risks: list[dict[str, Any]],
    missing_items: list[str],
    detected_topics: list[str],
) -> list[str]:
    """根据命中规则与缺失项生成简短建议（中文）。"""
    recs: list[str] = []
    rule_ids = {str(r.get("rule_id") or "") for r in risks}

    if "deposit_amount_high" in rule_ids:
        recs.append(
            "请核对押金是否已按当地要求存入政府认可的托管计划（如 DPS、TDS、MyDeposits），并保存证书。"
        )

    fee_ids = {"fee_suspicious_generic", "fee_penalty", "fee_non_refundable", "fee_admin_cleaning"}
    if rule_ids & fee_ids:
        recs.append("逐项核对费用名称与金额；避免将本不应单独收取的项目与押金或首月租金混同。")

    if (
        "landlord_enter_anytime" in rule_ids
        or "no_notice_termination" in rule_ids
        or "access_no_notice_bad" in rule_ids
    ):
        recs.append("对进入权、通知期与解约程序有疑问时，建议对照当地现行租赁法规或咨询 Citizens Advice 类渠道。")

    if "landlord_enter_anytime" in rule_ids or "access_no_notice_bad" in rule_ids:
        recs.append("进入权条款应写明合理通知时间与紧急情况例外；若与口头承诺不一致，以书面条款为准。")

    if "tenant_all_repairs" in rule_ids:
        recs.append("结构性维修与房东法定义务通常不可通过合同全部转嫁给租客；建议请专业人士审阅维修条款范围。")

    if "rent_increase_unfair" in rule_ids:
        recs.append("涨租条款若过于宽泛，可要求出租方明确程序、频率与通知期。")

    if "deposit_not_protected_text" in rule_ids:
        recs.append("若合同暗示押金未托管，签约前应要求书面澄清托管方案与证书。")

    if _missing_covers_notice_and_repair(missing_items):
        recs.append("正文若未同时写明通知期与维修责任，建议索取标准条款或让房东确认补充后再签署。")

    if len(missing_items) >= 6:
        recs.append("缺失主题较多时，可要求对方提供标准条款附录或修订后再签署。")
    elif missing_items:
        recs.append("对合同中未明确写清的主题，可要求出租方在签约前以书面补充条款或附录说明。")

    if not detected_topics:
        recs.append("若正文极短或未包含常见条款关键词，建议换用完整合同 PDF/全文再分析。")

    recs.append("本分析基于关键词与简单规则，不构成法律意见；签约前请通读全文并保留沟通记录。")

    return _uniq_preserve(recs)


def analyze_contract_text(contract_input: ContractInput) -> dict[str, Any]:
    """
    对合同文本做基础规则分析。

    返回 dict 字段：
    - summary: str
    - risks: list[dict]（title / severity / reason，可能含 rule_id）
    - missing_items: list[str]
    - recommendations: list[str]
    - detected_topics: list[str]（已覆盖主题的人类可读标签）
    """
    text = (contract_input.contract_text or "").strip()
    if not text:
        return _normalize_analysis_output(
            {
                "summary": "未提供合同文本，无法分析。",
                "risks": [],
                "missing_items": ["合同正文"],
                "recommendations": ["请上传或粘贴完整合同文本后再试。"],
                "detected_topics": [],
            }
        )

    detected_topics = detect_contract_topics(text)
    risks = detect_contract_risks(text, contract_input)
    missing_items = detect_missing_items(text)
    recommendations = build_recommendations(risks, missing_items, detected_topics)
    summary = build_contract_summary(risks, missing_items, detected_topics)

    return _normalize_analysis_output(
        {
            "summary": summary,
            "risks": risks,
            "missing_items": missing_items,
            "recommendations": recommendations,
            "detected_topics": detected_topics,
        }
    )
