"""
Phase B7：合同完整性 / 风险综合报告层（rule-based）。
整合 detected_risks、missing_clauses、summary，生成便于前端展示或导出的 contract_report。
"""

from __future__ import annotations

import re
from typing import Any

from contract_missing_clauses import analyze_all_clause_statuses

# --- clause_key → 条款写清时的正向表述（用于 strengths）---
_CLAUSE_STRENGTH_LABEL: dict[str, str] = {
    "deposit_terms": "押金及扣减/保护相关条款有一定覆盖",
    "rent_terms": "租金金额与支付安排有书面约定",
    "repair_responsibility": "维修或维护责任有区分表述",
    "termination_terms": "解约或提前终止相关条款有出现",
    "notice_terms": "通知期或书面通知形式有约定",
    "fee_terms": "额外费用及触发条件有说明",
    "basic_property_or_tenancy_scope": "租期或租赁标的描述较完整",
}

_RISK_TYPE_LABEL: dict[str, str] = {
    "deposit": "押金",
    "rent_increase": "涨租",
    "repairs": "维修责任",
    "termination": "解约/终止",
    "fees": "费用",
    "notice": "通知",
}


def _severity_order(r: dict[str, Any]) -> int:
    s = r.get("severity") or "low"
    return {"high": 3, "medium": 2, "low": 1}.get(s, 0)


def _compute_overall_verdict(
    summary: dict[str, Any],
    missing_clauses: list[dict[str, Any]],
) -> str:
    """
    overall_verdict 判断逻辑：high_risk / caution / safe（rule-based）。
    """
    high_n = int(summary.get("high_risk_count") or 0)
    med_n = int(summary.get("medium_risk_count") or 0)
    comp = summary.get("completeness_level") or "medium"
    miss_n = int(summary.get("missing_clause_count") or 0)
    part_n = int(summary.get("partial_missing_count") or 0)
    missing_high_n = sum(1 for m in missing_clauses if (m.get("severity") or "") == "high")

    # high_risk：扫描命中多项高风险，或缺失条款中多项为 high severity
    if high_n >= 2 or missing_high_n >= 2:
        return "high_risk"
    # 完整性极低且有关键缺口或仍有高风险命中
    if comp == "low" and (miss_n >= 2 or high_n >= 1):
        return "high_risk"

    # safe：风险较少且条款完整性高、缺口很少
    if (
        high_n == 0
        and med_n == 0
        and miss_n == 0
        and part_n <= 1
        and comp == "high"
    ):
        return "safe"

    # caution：存在中风险、partial_missing 较多、或完整性一般/偏低
    if med_n >= 1 or miss_n >= 1 or part_n >= 3 or comp in ("medium", "low"):
        return "caution"
    if high_n == 1:
        return "caution"
    return "caution"


def _compute_overall_score(
    detected_risks: list[dict[str, Any]],
    missing_clauses: list[dict[str, Any]],
) -> int:
    """
    overall_score：初始 100，按风险与条款缺口扣分，限制在 0–100。
    """
    score = 100
    for r in detected_risks:
        sev = r.get("severity") or "low"
        if sev == "high":
            score -= 20
        elif sev == "medium":
            score -= 10
        else:
            score -= 5
    for m in missing_clauses:
        st = m.get("status") or ""
        if st == "missing":
            score -= 15
        elif st == "partial_missing":
            score -= 8
    return max(0, min(100, score))


def _pick_key_issues(
    detected_risks: list[dict[str, Any]],
    missing_clauses: list[dict[str, Any]],
    limit: int = 3,
) -> list[str]:
    """从风险与缺失条款中抽取最重要若干条（中文短句）。"""
    issues: list[str] = []
    ranked_r = sorted(detected_risks, key=_severity_order, reverse=True)
    for r in ranked_r[:3]:
        reason = (r.get("reason") or "").strip()
        rt = r.get("risk_type")
        label = _RISK_TYPE_LABEL.get(str(rt), str(rt)) if rt else ""
        if reason:
            prefix = ("【%s】" % label) if label else ""
            line = (prefix + reason).strip()
            if line not in issues:
                issues.append(line[:120])
    ranked_m = sorted(
        missing_clauses,
        key=lambda m: {"high": 3, "medium": 2, "low": 1}.get(m.get("severity") or "low", 0),
        reverse=True,
    )
    for m in ranked_m[:3]:
        reason = (m.get("reason") or "").strip()
        if reason and reason not in issues:
            issues.append(reason[:120])
    return issues[:limit]


def _pick_strengths(
    contract_text: str,
    detected_risks: list[dict[str, Any]],
) -> list[str]:
    """从条款 present 状态与低风险扫描结果生成 strengths（最多 4 条）。"""
    out: list[str] = []
    statuses = analyze_all_clause_statuses(contract_text)
    for key, st in statuses.items():
        if st == "present":
            line = _CLAUSE_STRENGTH_LABEL.get(key)
            if line and line not in out:
                out.append(line)
        if len(out) >= 4:
            break
    if not out and not detected_risks:
        return ["当前文本未触发高风险规则，仍建议全文人工复核"]
    if not out and detected_risks and all((r.get("severity") == "low") for r in detected_risks):
        return ["已识别风险项整体严重度偏低", "建议仍结合适用法律与个案核对"]
    if len(out) < 2 and detected_risks and all((r.get("severity") == "low") for r in detected_risks):
        extra = "已识别条款风险以低级别为主"
        if extra not in out:
            out.append(extra)
    if not out and detected_risks:
        out.append("关键风险点已列出，可按优先级逐项核对")
    return out[:4]


def _pick_priority_actions(
    detected_risks: list[dict[str, Any]],
    missing_clauses: list[dict[str, Any]],
) -> list[str]:
    """优先取 high/medium 风险对应的 recommendation_action，并补充缺失条款 suggestion。"""
    from contract_action_mapping import NEXT_STEP_LINE_BY_TYPE, get_action_priority

    actions: list[str] = []
    ranked = sorted(
        detected_risks,
        key=lambda r: (
            {"high": 3, "medium": 2, "low": 1}.get(get_action_priority(r), 0),
            _severity_order(r),
        ),
        reverse=True,
    )
    for r in ranked:
        rec = (r.get("recommendation_action") or "").strip()
        if rec and rec not in actions:
            actions.append(rec[:200])
        if len(actions) >= 3:
            break
    if len(actions) < 3:
        for m in missing_clauses:
            if (m.get("severity") or "") != "high":
                continue
            sug = (m.get("suggestion") or "").strip()
            if sug and sug not in actions:
                actions.append(sug[:200])
            if len(actions) >= 5:
                break
    if len(actions) < 3:
        for m in missing_clauses:
            sug = (m.get("suggestion") or "").strip()
            if sug and sug not in actions:
                actions.append(sug[:200])
            if len(actions) >= 5:
                break
    # 用类型短句补足（与 B4 一致）
    if len(actions) < 3:
        for r in ranked:
            rt = r.get("risk_type")
            line = NEXT_STEP_LINE_BY_TYPE.get(str(rt)) if rt else None
            if line and line not in actions:
                actions.append(line)
            if len(actions) >= 3:
                break
    if not actions:
        actions.append("通读合同全文，对未列明事项要求书面补充")
    return actions[:5]


def _risk_overview_text(
    verdict: str,
    summary: dict[str, Any],
    key_issues: list[str],
) -> str:
    """一句总体说明：结合整体风险等级与主要问题主题。"""
    overall = summary.get("overall_level") or "low"
    level_cn = {"high": "较高", "medium": "中等", "low": "较低"}.get(str(overall), "一定")
    short = [re.sub(r"^【[^】]+】", "", x).strip()[:32] for x in key_issues[:3]]
    topics = "、".join(s for s in short if s)
    if verdict == "high_risk":
        head = "合同整体风险偏高"
    elif verdict == "caution":
        head = "合同存在一定风险与待澄清点"
    else:
        head = "合同整体相对可控"
    if topics:
        return "%s，综合风险等级为%s；主要关注点包括：%s。" % (head, level_cn, topics)
    return "%s，综合风险等级为%s；建议仍通读全文并核对适用法律。" % (head, level_cn)


def _signing_recommendation(verdict: str) -> str:
    if verdict == "safe":
        return "可继续推进，但仍建议核对关键条款与适用法律"
    if verdict == "caution":
        return "建议补充和确认关键条款后再签约"
    return "当前合同风险较高，不建议在未修订或书面澄清前直接签约"


def _one_line_summary(
    verdict: str,
    summary: dict[str, Any],
    key_issues: list[str],
) -> str:
    v_cn = {"safe": "整体较稳妥", "caution": "中等风险", "high_risk": "风险偏高"}.get(
        verdict, "待评估"
    )
    comp = summary.get("completeness_level") or ""
    comp_bit = (
        "条款完整性较好"
        if comp == "high"
        else ("条款完整性一般" if comp == "medium" else "条款完整性不足")
    )
    hint = ""
    if key_issues:
        hint = key_issues[0][:40].replace("【", "").replace("】", "")
    tail = "建议补充核对后再签约" if verdict != "safe" else "签约前仍建议复核要点"
    if hint:
        return "%s，%s；%s…%s" % (v_cn, comp_bit, hint, tail)
    return "%s，%s；%s" % (v_cn, comp_bit, tail)


def build_contract_report(
    contract_text: str,
    detected_risks: list[dict[str, Any]],
    missing_clauses: list[dict[str, Any]],
    summary: dict[str, Any],
) -> dict[str, Any]:
    """
    生成 contract_report：overall_verdict / score、概述、要点、优势、优先行动、签约建议、一行摘要。
    """
    verdict = _compute_overall_verdict(summary, missing_clauses)
    score = _compute_overall_score(detected_risks, missing_clauses)
    key_issues = _pick_key_issues(detected_risks, missing_clauses)
    strengths = _pick_strengths(contract_text, detected_risks)
    priority_actions = _pick_priority_actions(detected_risks, missing_clauses)
    overview = _risk_overview_text(verdict, summary, key_issues)
    signing = _signing_recommendation(verdict)
    one_line = _one_line_summary(verdict, summary, key_issues)

    return {
        "overall_verdict": verdict,
        "overall_score": score,
        "risk_overview": overview,
        "key_issues": key_issues[:5],
        "strengths": strengths,
        "priority_actions": priority_actions,
        "signing_recommendation": signing,
        "one_line_summary": one_line,
    }
