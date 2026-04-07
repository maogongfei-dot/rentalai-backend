"""
Contract analysis console presentation: envelope from ``run_contract_analysis`` (Phase 3 Part 25).

Phase 4 Part 5 — optional ``final_display`` unified user-facing block with legacy fallback.
"""

from __future__ import annotations

from typing import Any


def _fd_str(v: Any) -> str:
    if v is None:
        return ""
    s = str(v).strip()
    return s


def _pick_title(envelope: dict[str, Any]) -> str:
    summary = envelope.get("summary") if isinstance(envelope.get("summary"), dict) else {}
    verdict = envelope.get("verdict") if isinstance(envelope.get("verdict"), dict) else {}
    rl = summary.get("risk_level")
    st = verdict.get("status")
    if rl == "high" or st == "high_risk":
        return "合同风险分析结果"
    return "租房合同分析结果"


def _pick_summary_block(envelope: dict[str, Any]) -> str:
    """One short Chinese conclusion; prefers human verdict-like fields, then rule-based."""
    if envelope.get("ok") is not True:
        return "本次未成功完成分析，请检查输入或稍后重试。"

    hv = envelope.get("human_verdict")
    if isinstance(hv, str) and hv.strip():
        return hv.strip()[:240]
    if isinstance(hv, dict):
        m = hv.get("message") or hv.get("summary")
        if isinstance(m, str) and m.strip():
            return m.strip()[:240]

    fv = envelope.get("final_verdict")
    if isinstance(fv, str) and fv.strip():
        return fv.strip()[:240]
    if isinstance(fv, dict):
        m = fv.get("message") or fv.get("summary")
        if isinstance(m, str) and m.strip():
            return m.strip()[:240]

    verdict = envelope.get("verdict") if isinstance(envelope.get("verdict"), dict) else {}
    summary = envelope.get("summary") if isinstance(envelope.get("summary"), dict) else {}
    rl = summary.get("risk_level")
    st = verdict.get("status")

    if st == "high_risk" or rl == "high":
        return "整体看，这份合同存在需要重点确认的风险，建议先补证据再继续。"
    if rl == "medium":
        return "部分条款可能不够清晰或存在一定风险，建议先核对后再签字。"
    if rl == "low":
        if st == "review_needed":
            return "整体风险相对可控，但仍有一些条款需要补齐或确认。"
        if st == "acceptable_with_review":
            return "整体看没有特别突出的高风险信号，但仍建议通读全文后再签字。"
    if st == "manual_review":
        return "系统结论不够确定，建议你结合材料自行判断，不要仅凭本结果做决定。"
    if st == "review_needed":
        return "有若干点需要先弄清楚或补证据，再决定是否签署。"

    he = summary.get("human_explanation") if isinstance(summary, dict) else None
    if isinstance(he, str) and he.strip():
        t = he.strip()
        return t[:200] + ("…" if len(t) > 200 else "")

    return "分析已完成，请结合下方说明与提醒查看要点。"


def _pick_explanation_block(envelope: dict[str, Any]) -> str:
    summary = envelope.get("summary")
    if isinstance(summary, dict):
        h = summary.get("human_explanation") or summary.get("explanation")
        if isinstance(h, str) and h.strip():
            return h.strip()
    details = envelope.get("details")
    if isinstance(details, dict):
        expl = details.get("explanations")
        if isinstance(expl, dict):
            h2 = expl.get("human_explanation") or expl.get("overall_explanation")
            if isinstance(h2, str) and h2.strip():
                return h2.strip()
    return ""


def _copy_str_list(raw: Any, max_n: int = 8) -> list[str]:
    if not isinstance(raw, list):
        return []
    out: list[str] = []
    for x in raw:
        if isinstance(x, str) and x.strip():
            out.append(x.strip())
        if len(out) >= max_n:
            break
    return out


def _extract_contract_text_length(envelope: dict[str, Any]) -> int:
    """Best-effort length from parsed output and optional user/description fields."""
    if not isinstance(envelope, dict):
        return 0
    n = 0
    parsed = (envelope.get("details") or {}).get("parsed") if isinstance(envelope.get("details"), dict) else {}
    if isinstance(parsed, dict):
        raw = parsed.get("length")
        if isinstance(raw, int) and raw > 0:
            n = raw
        else:
            n = len(str(parsed.get("raw_text") or ""))
        secs = parsed.get("sections")
        if isinstance(secs, list) and secs and n < 10:
            n = max(n, sum(len(str(s)) for s in secs[:5]))
    for k in ("user_input", "complaint_text", "description", "scenario", "contract_text"):
        v = envelope.get(k)
        if isinstance(v, str) and v.strip():
            n = max(n, len(v.strip()))
    return n


def _risk_items_count(envelope: dict[str, Any]) -> int:
    det = envelope.get("details")
    if not isinstance(det, dict):
        return 0
    risk = det.get("risk")
    if not isinstance(risk, dict):
        return 0
    risks = risk.get("risks")
    if isinstance(risks, list):
        return len(risks)
    return 0


def build_analysis_completeness(system_result: dict[str, Any]) -> str:
    """
    Light rule: high / medium / low based on text length, clause gaps, and risk signals.
    """
    if not isinstance(system_result, dict) or system_result.get("ok") is not True:
        return "low"
    L = _extract_contract_text_length(system_result)
    mc = system_result.get("missing_clauses")
    n_miss = len(mc) if isinstance(mc, list) else 0
    n_risk = _risk_items_count(system_result)
    flagged = system_result.get("flagged_clauses")
    n_flag = len(flagged) if isinstance(flagged, list) else 0

    if L < 40:
        return "low"
    if L < 100 and n_miss >= 5 and n_risk <= 1:
        return "low"
    if L >= 160 and n_risk >= 2 and n_miss <= 3:
        return "high"
    if L >= 200 and n_risk >= 2:
        return "high"
    if L >= 90 and n_miss <= 3 and (n_risk >= 1 or n_flag >= 1):
        return "high"
    if L >= 55:
        return "medium"
    return "low"


def _missing_clause_to_analysis_hint(english_line: str) -> str | None:
    low = english_line.lower()
    if "deposit" in low:
        return "押金相关约定的完整条款或前后文（便于分析比对）"
    if "rent" in low:
        return "租金标准与支付方式的明确条款（分析侧仍不完整）"
    if "notice" in low:
        return "通知期、解约程序相关条款的完整表述"
    if "repair" in low or "maintenance" in low:
        return "维修责任与房屋状况相关条款"
    if "termination" in low or "tenancy" in low:
        return "租约终止与退租相关条款"
    if "fee" in low:
        return "各类费用与扣款条款的明确约定"
    return None


def build_missing_information(system_result: dict[str, Any]) -> list[str]:
    """
    What the *analysis* still lacks (not the same wording as evidence checklist).
    """
    if not isinstance(system_result, dict) or system_result.get("ok") is not True:
        return []
    items: list[str] = []
    L = _extract_contract_text_length(system_result)
    if L < 50:
        items.append("更长的合同原文或连续条款段落（当前样本偏短）")
    if L < 120:
        items.append("关键条款的上下文（租金、押金、解约、通知）以便交叉核对")

    mc = system_result.get("missing_clauses")
    if isinstance(mc, list):
        for m in mc:
            if not isinstance(m, str):
                continue
            hint = _missing_clause_to_analysis_hint(m)
            if hint and hint not in items:
                items.append(hint)
            if len(items) >= 5:
                break

    if system_result.get("issue_type") or system_result.get("scenario"):
        items.append("问题背景与时间线（若涉及具体纠纷）")

    seen: set[str] = set()
    out: list[str] = []
    for x in items:
        if x and x not in seen:
            seen.add(x)
            out.append(x)
        if len(out) >= 5:
            break
    return out


def build_human_missing_info_guidance(system_result: dict[str, Any]) -> str:
    """Short Chinese guidance; references ``analysis_completeness`` and ``missing_information``."""
    if not isinstance(system_result, dict) or system_result.get("ok") is not True:
        return ""
    comp = (system_result.get("analysis_completeness") or "low").lower()
    if comp not in ("high", "medium", "low"):
        comp = "low"

    if comp == "high":
        base = "目前信息相对完整，这次结果已经有较高参考价值。"
    elif comp == "medium":
        base = "目前可以做初步判断，但还有一些关键信息没有补齐，建议补充后再看。"
    else:
        base = "目前信息偏少，这次结果更适合作为初步提醒，暂时不适合直接当作最终结论。"

    missing = system_result.get("missing_information")
    if isinstance(missing, list) and missing:
        top = [m for m in missing if isinstance(m, str) and m.strip()][:3]
        if top:
            return base + "建议优先补充：" + "；".join(top) + "。"
    return base


def _completeness_label_zh(level: str) -> str:
    return {"high": "信息较完整", "medium": "信息部分完整", "low": "信息不足"}.get(
        level.lower() if isinstance(level, str) else "", "信息不足"
    )


def _decision_label_zh(code: str) -> str:
    return {
        "proceed": "可以继续",
        "caution": "谨慎继续",
        "pause": "建议先暂停确认",
        "escalate": "建议升级处理",
    }.get((code or "").lower(), "")


def _escalate_signal_from_texts(actions: list[Any], steps: list[Any]) -> bool:
    en_kw = (
        "legal",
        "tribunal",
        "complaint",
        "ombudsman",
        "council",
        "housing advice",
        "report",
        "court",
    )
    zh_kw = ("投诉", "法律", "申诉", "升级", "监管", "调解", "仲裁", "诉讼", "律师")
    parts: list[str] = []
    for a in actions or []:
        if isinstance(a, str):
            parts.append(a.lower())
    for s in steps or []:
        if isinstance(s, str):
            parts.append(s.lower())
    blob = " ".join(parts)
    if any(k in blob for k in en_kw):
        return True
    full = "".join(parts)
    return any(k in full for k in zh_kw)


def build_recommended_decision(system_result: dict[str, Any]) -> str:
    """English enum: proceed | caution | pause | escalate."""
    if not isinstance(system_result, dict) or system_result.get("ok") is not True:
        return "pause"
    verdict = system_result.get("verdict") if isinstance(system_result.get("verdict"), dict) else {}
    summary = system_result.get("summary") if isinstance(system_result.get("summary"), dict) else {}
    st = verdict.get("status")
    rl = summary.get("risk_level")
    sev = summary.get("severity")
    comp = (system_result.get("analysis_completeness") or "low").lower()
    if comp not in ("high", "medium", "low"):
        comp = "low"

    actions = system_result.get("actions") or []
    steps = system_result.get("human_next_steps") or []
    if _escalate_signal_from_texts(
        actions if isinstance(actions, list) else [],
        steps if isinstance(steps, list) else [],
    ):
        return "escalate"
    if isinstance(sev, str) and sev.lower() in ("critical", "severe"):
        return "escalate"
    if rl == "high" or st == "high_risk":
        return "escalate"
    if comp == "low":
        return "pause"
    if st == "manual_review":
        return "pause"
    if st == "review_needed" and rl == "low":
        return "pause"
    if rl == "medium" or st == "review_needed":
        return "caution"
    if rl == "low" and st == "acceptable_with_review":
        return "proceed"
    if rl == "low":
        return "proceed"
    return "caution"


def build_direct_answer(system_result: dict[str, Any]) -> str:
    """1–3 short sentences; does not copy ``human_explanation`` verbatim."""
    if not isinstance(system_result, dict) or system_result.get("ok") is not True:
        return "当前无法给出可靠结论，请检查输入或稍后重试。"

    d = build_recommended_decision(system_result)
    comp = (system_result.get("analysis_completeness") or "low").lower()
    if comp not in ("high", "medium", "low"):
        comp = "low"

    if d == "proceed":
        core = "目前看可以继续推进，但仍建议按步骤保留材料，重要约定尽量留痕。"
    elif d == "caution":
        core = "这件事可以继续处理，但要比平时更谨慎，先把关键条款和证据对齐再往下走。"
    elif d == "pause":
        core = "目前不建议匆忙做决定，最好先把缺失信息和关键风险点确认清楚。"
    else:
        core = "这类情况往往不适合只靠口头沟通解决，建议尽快进入更正式的处理路径。"

    if comp == "low":
        prefix = "当前内容更适合做初步参考，不宜当作最终结论。"
        return prefix + core

    return core


def _truncate_short_zh(text: str, max_chars: int = 26) -> str:
    t = text.strip()
    if len(t) <= max_chars:
        return t
    return t[: max_chars - 1].rstrip("，。 ") + "…"


def build_direct_answer_short(system_result: dict[str, Any]) -> str:
    """One line for cards; ~25 Chinese characters."""
    if not isinstance(system_result, dict) or system_result.get("ok") is not True:
        return "先检查输入再试。"

    d = build_recommended_decision(system_result)
    comp = (system_result.get("analysis_completeness") or "low").lower()
    if comp not in ("high", "medium", "low"):
        comp = "low"

    base = {
        "proceed": "可以继续，但仍建议留痕备查。",
        "caution": "谨慎推进，先确认条款与证据。",
        "pause": "先暂停，把信息和风险弄清。",
        "escalate": "建议尽快走正式处理路径。",
    }.get(d, "先暂停，把信息和风险弄清。")

    if comp == "low":
        base = "初步参考：" + base
    return _truncate_short_zh(base, 28)


def _confidence_label_zh(level: str) -> str:
    return {"high": "参考度较高", "medium": "参考度中等", "low": "参考度较低"}.get(
        (level or "").lower(), ""
    )


def _count_support_layers(envelope: dict[str, Any]) -> int:
    """How many of explanation / next steps / evidence are present (for confidence)."""
    n = 0
    if _fd_str(_pick_explanation_block(envelope)):
        n += 1
    if _copy_str_list(envelope.get("human_next_steps")):
        n += 1
    if _copy_str_list(envelope.get("human_evidence_checklist")):
        n += 1
    return n


def build_result_confidence(system_result: dict[str, Any]) -> str:
    """
    English enum high | medium | low — how much to trust this analysis output (not risk level).
    """
    if not isinstance(system_result, dict) or system_result.get("ok") is not True:
        return "low"
    comp = (system_result.get("analysis_completeness") or "low").lower()
    if comp not in ("high", "medium", "low"):
        comp = "low"
    if comp == "low":
        return "low"

    L = _extract_contract_text_length(system_result)
    n_risk = _risk_items_count(system_result)
    flagged = system_result.get("flagged_clauses") or []
    n_flag = len(flagged) if isinstance(flagged, list) else 0
    verdict = system_result.get("verdict") if isinstance(system_result.get("verdict"), dict) else {}
    has_st = bool(verdict.get("status"))
    layers = _count_support_layers(system_result)
    rd = (system_result.get("recommended_decision") or "").lower()

    if comp == "medium":
        if layers >= 2 and (n_risk >= 1 or n_flag >= 1) and L >= 60:
            return "medium"
        if layers >= 1 and L >= 50:
            return "medium"
        return "low"

    # comp == high
    if L < 70:
        return "medium"
    if not has_st:
        return "medium"
    if n_risk < 1 and n_flag < 1:
        return "medium"
    if layers < 2:
        return "medium"
    if rd == "escalate" and L < 120:
        return "medium"
    return "high"


def build_confidence_reason(system_result: dict[str, Any]) -> str:
    """One short sentence: why this confidence level (distinct from completeness wording)."""
    if not isinstance(system_result, dict) or system_result.get("ok") is not True:
        return "当前无法评估本次结果的参考强度。"
    rc = build_result_confidence(system_result)
    if rc == "high":
        return (
            "因为已有较完整的条款与风险识别，并附了说明、步骤与材料建议，"
            "本次输出的参考强度相对较高。"
        )
    if rc == "medium":
        return (
            "因为信息仍偏部分，系统能给出方向性判断，但参考强度有限，不宜完全依赖。"
        )
    return (
        "因为缺少足够条款与材料支撑，本次输出更适合当作提醒，不适合单独作为决策依据。"
    )


def build_human_confidence_notice(system_result: dict[str, Any]) -> str:
    """How the user should interpret this result (not legal advice)."""
    if not isinstance(system_result, dict) or system_result.get("ok") is not True:
        return "请先完成分析，再理解本次结果的参考强度。"
    rc = build_result_confidence(system_result)
    if rc == "high":
        return "可以把这次结果当作较强参考，但正式处理前仍建议保留关键材料与记录。"
    if rc == "medium":
        return "建议把这次结果当作方向参考，重要决定前再核对条款与证据。"
    return "请不要只凭这次结果做最终决定，先补齐信息与材料后再判断。"


def build_final_display(system_result: dict[str, Any]) -> dict[str, Any]:
    """
    Unified user-facing display object (Phase 4 Part 5).

    Safe on missing fields; ``meta_block`` placeholders filled later by ``main`` shell merge.
    """
    if not isinstance(system_result, dict):
        return {
            "title": "",
            "direct_answer_block": "",
            "direct_answer_short_block": "",
            "decision_block": "",
            "confidence_block": "",
            "confidence_reason_block": "",
            "confidence_notice_block": "",
            "summary_block": "",
            "risk_block": "",
            "explanation_block": "",
            "completeness_block": "",
            "missing_info_block": [],
            "guidance_block": "",
            "next_steps_block": [],
            "evidence_block": [],
            "meta_block": {"source": "", "request_id": "", "timestamp": ""},
        }

    next_steps = (
        system_result.get("human_next_steps")
        or system_result.get("next_steps_block")
        or _copy_str_list(system_result.get("recommended_actions"))
        or _copy_str_list(system_result.get("next_steps"))
    )
    evidence = (
        system_result.get("human_evidence_checklist")
        or system_result.get("evidence_block")
        or _copy_str_list(system_result.get("required_evidence"))
        or _copy_str_list(system_result.get("evidence_list"))
    )

    risk_block = _fd_str(system_result.get("human_risk_warning"))
    if not risk_block:
        issue = system_result.get("issue_summary")
        if isinstance(issue, str) and issue.strip():
            risk_block = issue.strip()[:300]

    ac = (system_result.get("analysis_completeness") or "low").lower()
    if ac not in ("high", "medium", "low"):
        ac = "low"

    rd = _fd_str(system_result.get("recommended_decision")).lower()
    if rd not in ("proceed", "caution", "pause", "escalate"):
        rd = build_recommended_decision(system_result)

    da = _fd_str(system_result.get("direct_answer")) or build_direct_answer(system_result)
    das = _fd_str(system_result.get("direct_answer_short")) or build_direct_answer_short(system_result)

    rc = _fd_str(system_result.get("result_confidence")).lower()
    if rc not in ("high", "medium", "low"):
        rc = build_result_confidence(system_result)
    cre = _fd_str(system_result.get("confidence_reason")) or build_confidence_reason(system_result)
    hcn = _fd_str(system_result.get("human_confidence_notice")) or build_human_confidence_notice(
        system_result
    )

    return {
        "title": _pick_title(system_result),
        "direct_answer_block": da,
        "direct_answer_short_block": das,
        "decision_block": _decision_label_zh(rd),
        "confidence_block": _confidence_label_zh(rc),
        "confidence_reason_block": cre,
        "confidence_notice_block": hcn,
        "summary_block": _pick_summary_block(system_result),
        "risk_block": risk_block,
        "explanation_block": _pick_explanation_block(system_result),
        "completeness_block": _completeness_label_zh(ac),
        "missing_info_block": _copy_str_list(system_result.get("missing_information"), 5),
        "guidance_block": _fd_str(system_result.get("human_missing_info_guidance")),
        "next_steps_block": _copy_str_list(next_steps),
        "evidence_block": _copy_str_list(evidence),
        "meta_block": {"source": "", "request_id": "", "timestamp": ""},
    }


def _format_unified_final_display(final_output: dict[str, Any], fd: dict[str, Any]) -> str:
    """CLI block from ``final_display`` + compact supplement (no duplicate human text)."""
    lines: list[str] = []
    title = _fd_str(fd.get("title")) or "租房合同分析结果"
    lines.append("=" * 30)
    lines.append(title)
    lines.append("=" * 30)

    da = _fd_str(fd.get("direct_answer_block"))
    if da:
        lines.append("")
        lines.append("直接回答：")
        lines.append(da)
    das = _fd_str(fd.get("direct_answer_short_block"))
    if das:
        lines.append("")
        lines.append("一句话：")
        lines.append(das)
    dec = _fd_str(fd.get("decision_block"))
    if dec:
        lines.append("")
        lines.append("建议状态：")
        lines.append(dec)

    cfb = _fd_str(fd.get("confidence_block"))
    if cfb:
        lines.append("")
        lines.append("结果参考度：")
        lines.append(cfb)
    crb = _fd_str(fd.get("confidence_reason_block"))
    if crb:
        lines.append("")
        lines.append("参考说明：")
        lines.append(crb)
    cnb = _fd_str(fd.get("confidence_notice_block"))
    if cnb:
        lines.append("")
        lines.append("使用提醒：")
        lines.append(cnb)

    sb = _fd_str(fd.get("summary_block"))
    if sb:
        lines.append("")
        lines.append("结论：")
        lines.append(sb)

    rb = _fd_str(fd.get("risk_block"))
    if rb:
        lines.append("")
        lines.append("风险提醒：")
        lines.append(rb)

    eb = _fd_str(fd.get("explanation_block"))
    if eb:
        lines.append("")
        lines.append("说明：")
        lines.append(eb)

    comp_l = _fd_str(fd.get("completeness_block"))
    if comp_l:
        lines.append("")
        lines.append("信息完整度：")
        lines.append(comp_l)

    gb = _fd_str(fd.get("guidance_block"))
    if gb:
        lines.append("")
        lines.append("补充说明：")
        lines.append(gb)

    mib = fd.get("missing_info_block")
    mi_lines = _copy_str_list(mib, 5) if isinstance(mib, list) else []
    if mi_lines:
        lines.append("")
        lines.append("当前还缺这些信息：")
        for s in mi_lines:
            lines.append(f"- {s}")

    steps = fd.get("next_steps_block")
    step_lines = _copy_str_list(steps, max_n=12) if isinstance(steps, list) else []
    if step_lines:
        lines.append("")
        lines.append("建议你下一步这样做：")
        for i, s in enumerate(step_lines, 1):
            lines.append(f"{i}. {s}")

    ev = fd.get("evidence_block")
    ev_lines = _copy_str_list(ev, max_n=12) if isinstance(ev, list) else []
    if ev_lines:
        lines.append("")
        lines.append("建议准备这些材料：")
        for s in ev_lines:
            lines.append(f"- {s}")

    meta = fd.get("meta_block")
    if isinstance(meta, dict):
        src = _fd_str(meta.get("source"))
        rid = _fd_str(meta.get("request_id"))
        ts = _fd_str(meta.get("timestamp"))
        if src or rid or ts:
            lines.append("")
            lines.append("请求信息：")
            if src:
                lines.append(f"- source: {src}")
            if rid:
                lines.append(f"- request_id: {rid}")
            if ts:
                lines.append(f"- timestamp: {ts}")

    # Compact supplement: missing / flagged only (no repeated verdict / human explanation)
    if final_output.get("ok"):
        missing = final_output.get("missing_clauses") or []
        flagged = final_output.get("flagged_clauses") or []
        if (isinstance(missing, list) and missing) or (isinstance(flagged, list) and flagged):
            lines.append("")
            lines.append("--- 补充（条款定位）---")
            if isinstance(missing, list) and missing:
                lines.append("可能缺失的条款提示：")
                for item in missing:
                    lines.append(f"- {item}")
            if isinstance(flagged, list) and flagged:
                lines.append("需要留意的原文片段：")
                for item in flagged:
                    lines.append(f"- {item}")

    return "\n".join(lines)


def _format_legacy_contract_result_text(final_output: dict[str, Any]) -> str:
    """Phase 4 Part 1–4 layout (fallback when ``final_display`` absent or unusable)."""
    lines: list[str] = ["=== Contract Analysis Result ==="]
    lines.append(f"Module: {final_output.get('module')}")
    lines.append(f"OK: {final_output.get('ok')}")
    verdict = final_output.get("verdict")
    if verdict:
        lines.append(f"Verdict status: {verdict.get('status')}")
        lines.append(f"Verdict title: {verdict.get('title')}")
        lines.append(f"Verdict message: {verdict.get('message')}")
    if final_output.get("ok"):
        summary = final_output.get("summary") or {}
        if not isinstance(summary, dict):
            summary = {}
        lines.append(f"Risk level: {summary.get('risk_level')}")
        lines.append(f"Explanation: {summary.get('overall_explanation')}")
        lines.append(f"Human explanation: {summary.get('human_explanation')}")

        da = final_output.get("direct_answer")
        if isinstance(da, str) and da.strip():
            lines.append("")
            lines.append("直接回答：")
            lines.append(da.strip())
        das = final_output.get("direct_answer_short")
        if isinstance(das, str) and das.strip():
            lines.append("")
            lines.append("一句话：")
            lines.append(das.strip())
        rd = final_output.get("recommended_decision")
        if isinstance(rd, str) and rd.lower() in ("proceed", "caution", "pause", "escalate"):
            lines.append("")
            lines.append("建议状态：")
            lines.append(_decision_label_zh(rd))

        rconf = final_output.get("result_confidence")
        if isinstance(rconf, str) and rconf.lower() in ("high", "medium", "low"):
            lines.append("")
            lines.append("结果参考度：")
            lines.append(_confidence_label_zh(rconf))
        cr = final_output.get("confidence_reason")
        if isinstance(cr, str) and cr.strip():
            lines.append("")
            lines.append("参考说明：")
            lines.append(cr.strip())
        hcn = final_output.get("human_confidence_notice")
        if isinstance(hcn, str) and hcn.strip():
            lines.append("")
            lines.append("使用提醒：")
            lines.append(hcn.strip())

        hw = final_output.get("human_risk_warning")
        if isinstance(hw, str) and hw.strip():
            lines.append("")
            lines.append("风险提醒：")
            lines.append(hw.strip())

        h_steps = final_output.get("human_next_steps") or []
        step_lines = (
            [s.strip() for s in h_steps if isinstance(s, str) and s.strip()]
            if isinstance(h_steps, list)
            else []
        )
        if step_lines:
            lines.append("")
            lines.append("建议你下一步这样做：")
            for i, s in enumerate(step_lines, 1):
                lines.append(f"{i}. {s}")

        h_ev = final_output.get("human_evidence_checklist") or []
        ev_lines = (
            [s.strip() for s in h_ev if isinstance(s, str) and s.strip()]
            if isinstance(h_ev, list)
            else []
        )
        if ev_lines:
            lines.append("")
            lines.append("建议准备这些材料：")
            for s in ev_lines:
                lines.append(f"- {s}")

        ac = final_output.get("analysis_completeness")
        _clab = {"high": "信息较完整", "medium": "信息部分完整", "low": "信息不足"}
        if isinstance(ac, str) and ac.lower() in _clab:
            lines.append("")
            lines.append("信息完整度：")
            lines.append(_clab[ac.lower()])
        hg = final_output.get("human_missing_info_guidance")
        if isinstance(hg, str) and hg.strip():
            lines.append("")
            lines.append("补充说明：")
            lines.append(hg.strip())
        mi = final_output.get("missing_information") or []
        if isinstance(mi, list) and mi:
            mil = [s.strip() for s in mi if isinstance(s, str) and s.strip()]
            if mil:
                lines.append("")
                lines.append("当前还缺这些信息：")
                for s in mil:
                    lines.append(f"- {s}")

        lines.append("Actions:")
        for action in final_output.get("actions") or []:
            lines.append(f"- {action}")
        lines.append("Missing clauses:")
        missing = final_output.get("missing_clauses")
        if missing:
            for item in missing:
                lines.append(f"- {item}")
        else:
            lines.append("- None detected")
        lines.append("Flagged clauses:")
        flagged = final_output.get("flagged_clauses")
        if flagged:
            for item in flagged:
                lines.append(f"- {item}")
        else:
            lines.append("- None detected")
    else:
        lines.append(f"Error: {final_output.get('error')}")
    return "\n".join(lines)


def _final_display_usable(fd: Any) -> bool:
    if not isinstance(fd, dict) or not fd:
        return False
    return bool(_fd_str(fd.get("title")) or _fd_str(fd.get("summary_block")))


def format_contract_result_text(final_output: dict[str, Any]) -> str:
    """
    Build a multi-line text block for the full contract envelope (module, verdict, risk, lists).

    Phase 4 Part 5: prefers ``final_display`` when present; otherwise legacy layout.
    """
    fd = final_output.get("final_display")
    if isinstance(fd, dict) and _final_display_usable(fd):
        return _format_unified_final_display(final_output, fd)
    return _format_legacy_contract_result_text(final_output)


def print_contract_result(final_output: dict[str, Any]) -> None:
    """Print ``run_contract_analysis`` envelope (module, verdict, risk, actions, locators)."""
    print(format_contract_result_text(final_output))
