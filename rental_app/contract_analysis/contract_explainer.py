"""
Phase 3 合同分析：Explain 输出层 —— 将 ``analyze_contract_text`` 的结构化结果转为人话说明。

风格对齐 RentalAI 常见「结论 + 摘要 + 建议」表述；纯规则拼接，无 LLM。
"""

from __future__ import annotations

import re
from typing import Any, cast

from .contract_analyzer import build_risk_category_summary, group_risks_by_category
from .contract_models import (
    ContractExplainResult,
    HighlightedRiskClause,
    coerce_contract_clause_type,
    coerce_contract_risk_category,
)

_CLAUSE_PREVIEW_CHARS = 120
_SHORT_REASON_CHARS = 120

_RE_CLAUSE_ID_NUM = re.compile(r"^clause_(\d+)$", re.IGNORECASE)


def _as_risk_list(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        return []
    return [x for x in raw if isinstance(x, dict)]


def _as_str_list(raw: Any) -> list[str]:
    if not isinstance(raw, list):
        return []
    return [str(x).strip() for x in raw if str(x).strip()]


def _as_clause_list(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        return []
    return [x for x in raw if isinstance(x, dict)]


def _short_clause_preview(text: str, max_len: int = _CLAUSE_PREVIEW_CHARS) -> str:
    """将条款正文压成短预览，便于卡片与 explain 列表。"""
    t = re.sub(r"\s+", " ", (text or "").strip())
    if len(t) <= max_len:
        return t
    return t[: max_len - 1] + "…"


def _clause_id_sort_key(clause_id: str) -> tuple[int, str]:
    m = _RE_CLAUSE_ID_NUM.match((clause_id or "").strip())
    return (int(m.group(1)), clause_id) if m else (10**9, clause_id)


def _find_risk_for_link(link: dict[str, Any], risks: list[dict[str, Any]]) -> dict[str, Any] | None:
    """用 title / matched_keyword / matched_text 与结构化 ``risks`` 对齐，便于取 ``reason``。"""
    rt = str(link.get("risk_title") or "").strip()
    mk = str(link.get("matched_keyword") or "").strip()
    mt = str(link.get("matched_text") or "").strip()
    for r in risks:
        if not isinstance(r, dict):
            continue
        if str(r.get("title") or "").strip() != rt:
            continue
        if mk and str(r.get("matched_keyword") or "").strip() == mk:
            return r
        if mt and str(r.get("matched_text") or "").strip() == mt:
            return r
    for r in risks:
        if isinstance(r, dict) and str(r.get("title") or "").strip() == rt:
            return r
    return None


def _normalize_severity(raw: Any) -> str:
    s = str(raw or "").strip().lower()
    return s if s in ("high", "medium", "low") else "medium"


def _build_clause_overview(clause_list: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """由结构化 ``clause_list`` 生成 explain 用条款清单（含截断预览）。"""
    out: list[dict[str, Any]] = []
    for c in clause_list:
        if not isinstance(c, dict):
            continue
        out.append(
            {
                "clause_id": str(c.get("clause_id") or "").strip(),
                "clause_type": coerce_contract_clause_type(c.get("clause_type")),
                "short_clause_preview": _short_clause_preview(str(c.get("clause_text") or "")),
                "matched_keywords": _as_str_list(c.get("matched_keywords")),
            }
        )
    return out


def _normalize_clause_overview(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        return []
    out: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        prev = str(item.get("short_clause_preview") or "").strip()
        if not prev and item.get("clause_text"):
            prev = _short_clause_preview(str(item.get("clause_text") or ""))
        elif len(prev) > _CLAUSE_PREVIEW_CHARS + 5:
            prev = _short_clause_preview(prev)
        mk = item.get("matched_keywords")
        if not isinstance(mk, list):
            mk = []
        mk = [str(x).strip() for x in mk if str(x).strip()]
        out.append(
            {
                "clause_id": str(item.get("clause_id") or "").strip(),
                "clause_type": coerce_contract_clause_type(item.get("clause_type")),
                "short_clause_preview": prev or "—",
                "matched_keywords": mk,
            }
        )
    return out


def _normalize_risk_category_groups(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        return []
    out: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        cat = coerce_contract_risk_category(item.get("category"))
        rs = item.get("risks")
        if not isinstance(rs, list):
            rs = []
        rs = [x for x in rs if isinstance(x, dict)]
        out.append({"category": cat, "risks": rs})
    return out


def _normalize_risk_category_summary(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        return []
    out: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        cat = coerce_contract_risk_category(item.get("category"))
        try:
            count = int(item.get("count", 0))
        except (TypeError, ValueError):
            count = 0
        hs_raw = str(item.get("highest_severity") or "low").strip().lower()
        hs = hs_raw if hs_raw in ("high", "medium", "low") else "medium"
        ss = str(item.get("short_summary") or "").strip()
        if not ss:
            sev_zh = {"high": "高", "medium": "中", "low": "低"}.get(hs, hs)
            ss = f"{cat}：共 {count} 条，最高「{sev_zh}」。"
        out.append(
            {
                "category": cat,
                "count": count,
                "highest_severity": hs,
                "short_summary": ss,
            }
        )
    return out


def _normalize_highlighted_clauses(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        return []
    out: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        hrc = {
            "risk_title": str(item.get("risk_title") or "").strip() or "—",
            "severity": str(item.get("severity") or "").strip() or "—",
            "matched_text": str(item.get("matched_text") or "").strip(),
            "location_hint": str(item.get("location_hint") or "").strip(),
            "short_advice": str(item.get("short_advice") or "").strip() or "—",
        }
        rcat = item.get("risk_category")
        hrc["risk_category"] = coerce_contract_risk_category(
            str(rcat).strip() if rcat is not None else None
        )
        rcode = item.get("risk_code")
        hrc["risk_code"] = (
            str(rcode).strip() if rcode is not None and str(rcode).strip() else "general"
        )
        out.append(hrc)
    return out


def _normalize_explain_out(ex: dict[str, Any]) -> dict[str, Any]:
    """保证 explain 字段齐全且类型稳定（含 ``highlighted_risk_clauses`` 与分类汇总）。"""
    adv = ex.get("action_advice")
    if not isinstance(adv, list):
        adv = []
    adv = [str(a).strip() for a in adv if str(a).strip()]
    while len(adv) < 3:
        adv.append("保留合同终稿与沟通记录，便于日后核对。")
    adv = adv[:5]
    hrc = _normalize_highlighted_clauses(ex.get("highlighted_risk_clauses"))
    rcg = _normalize_risk_category_groups(ex.get("risk_category_groups"))
    rcs = _normalize_risk_category_summary(ex.get("risk_category_summary"))
    cov = _normalize_clause_overview(ex.get("clause_overview"))
    cro = _normalize_clause_risk_overview(ex.get("clause_risk_overview"))
    cso = _normalize_clause_severity_overview(ex.get("clause_severity_overview"))
    return {
        "overall_conclusion": (str(ex.get("overall_conclusion") or "").strip() or "—"),
        "key_risk_summary": (str(ex.get("key_risk_summary") or "").strip() or "—"),
        "missing_clause_summary": (str(ex.get("missing_clause_summary") or "").strip() or "—"),
        "action_advice": adv,
        "highlighted_risk_clauses": hrc,
        "risk_category_groups": rcg,
        "risk_category_summary": rcs,
        "clause_overview": cov,
        "clause_risk_overview": cro,
        "clause_severity_overview": cso,
    }


def _severity_bucket(risks: list[dict[str, Any]]) -> tuple[int, int, int]:
    hi = md = lo = 0
    for r in risks:
        s = str(r.get("severity") or "").lower()
        if s == "high":
            hi += 1
        elif s == "medium":
            md += 1
        else:
            lo += 1
    return hi, md, lo


def _has_locatable_risk_text(risks: list[dict[str, Any]]) -> bool:
    return any(str(r.get("matched_text") or "").strip() for r in risks)


def _short_advice_from_risk(risk: dict[str, Any]) -> str:
    """从规则 reason 压缩为一条短建议（供卡片展示）。"""
    t = str(risk.get("reason") or "").strip()
    if not t:
        return "请对照原文与出租方书面确认该条款含义。"
    for sep in ("。", ".", ";", "；"):
        if sep in t:
            first = t.split(sep)[0].strip()
            if len(first) >= 12:
                t = first + ("。" if sep == "。" else "")
                break
    if len(t) > 160:
        t = t[:157] + "…"
    return t


def _short_reason_for_linked_risk(link: dict[str, Any], risks: list[dict[str, Any]]) -> str:
    r = _find_risk_for_link(link, risks)
    if r is not None:
        t = str(r.get("reason") or "").strip()
        if not t:
            t = _short_advice_from_risk(r)
        t = re.sub(r"\s+", " ", t)
        if len(t) > _SHORT_REASON_CHARS:
            t = t[: _SHORT_REASON_CHARS - 1] + "…"
        return t or "—"
    lr = str(link.get("link_reason") or "").strip()
    if len(lr) > _SHORT_REASON_CHARS:
        lr = lr[: _SHORT_REASON_CHARS - 1] + "…"
    return lr or "—"


def _build_clause_risk_overview(
    clause_list: list[dict[str, Any]],
    clause_risk_map: list[dict[str, Any]],
    risks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    按 ``clause_id`` 聚合 ``clause_risk_map``，并挂上 ``clause_type`` 与短预览（与 ``clause_overview`` 同截断长度）。
    无联动时返回空 list。
    """
    if not clause_risk_map:
        return []
    by_clause: dict[str, list[dict[str, Any]]] = {}
    for link in clause_risk_map:
        if not isinstance(link, dict):
            continue
        cid = str(link.get("clause_id") or "").strip()
        if not cid:
            continue
        by_clause.setdefault(cid, []).append(link)

    clause_by_id: dict[str, dict[str, Any]] = {}
    for c in clause_list:
        if not isinstance(c, dict):
            continue
        cid = str(c.get("clause_id") or "").strip()
        if cid:
            clause_by_id[cid] = c

    out: list[dict[str, Any]] = []
    for cid in sorted(by_clause.keys(), key=_clause_id_sort_key):
        c = clause_by_id.get(cid) or {}
        ct = coerce_contract_clause_type(c.get("clause_type"))
        preview = _short_clause_preview(str(c.get("clause_text") or ""))
        linked_risks: list[dict[str, Any]] = []
        for link in by_clause[cid]:
            linked_risks.append(
                {
                    "risk_title": str(link.get("risk_title") or "").strip() or "—",
                    "risk_category": coerce_contract_risk_category(link.get("risk_category")),
                    "severity": _normalize_severity(link.get("severity")),
                    "matched_keyword": str(link.get("matched_keyword") or "").strip(),
                    "short_reason": _short_reason_for_linked_risk(link, risks),
                }
            )
        out.append(
            {
                "clause_id": cid,
                "clause_type": ct,
                "short_clause_preview": preview or "—",
                "linked_risks": linked_risks,
            }
        )
    return out


def _normalize_clause_severity_overview(raw: Any) -> list[dict[str, Any]]:
    """
    Explain 层 ``clause_severity_overview``：由结构化 ``clause_severity_summary`` 映射，字段稳定、顺序一致。
    """
    if not isinstance(raw, list):
        return []
    out: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        cid = str(item.get("clause_id") or "").strip()
        if not cid:
            continue
        try:
            sc = int(item.get("severity_score", 0))
        except (TypeError, ValueError):
            sc = 0
        try:
            n = int(item.get("linked_risk_count", 0))
        except (TypeError, ValueError):
            n = 0
        hs = _normalize_severity(item.get("highest_severity"))
        titles = item.get("linked_risk_titles")
        if not isinstance(titles, list):
            titles = []
        titles = [str(t).strip() for t in titles if str(t).strip()]
        prev = str(item.get("short_clause_preview") or "").strip()
        if not prev:
            prev = "—"
        elif len(prev) > _CLAUSE_PREVIEW_CHARS + 5:
            prev = _short_clause_preview(prev)
        out.append(
            {
                "clause_id": cid,
                "clause_type": coerce_contract_clause_type(item.get("clause_type")),
                "severity_score": max(0, sc),
                "highest_severity": hs,
                "linked_risk_count": max(0, n),
                "short_clause_preview": prev,
                "linked_risk_titles": titles,
            }
        )
    return out


def _normalize_clause_risk_overview(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        return []
    out: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        prev = str(item.get("short_clause_preview") or "").strip()
        if not prev and item.get("clause_text"):
            prev = _short_clause_preview(str(item.get("clause_text") or ""))
        elif len(prev) > _CLAUSE_PREVIEW_CHARS + 5:
            prev = _short_clause_preview(prev)
        lr = item.get("linked_risks")
        if not isinstance(lr, list):
            lr = []
        linked: list[dict[str, Any]] = []
        for x in lr:
            if not isinstance(x, dict):
                continue
            linked.append(
                {
                    "risk_title": str(x.get("risk_title") or "").strip() or "—",
                    "risk_category": coerce_contract_risk_category(x.get("risk_category")),
                    "severity": _normalize_severity(x.get("severity")),
                    "matched_keyword": str(x.get("matched_keyword") or "").strip(),
                    "short_reason": str(x.get("short_reason") or "").strip() or "—",
                }
            )
        out.append(
            {
                "clause_id": str(item.get("clause_id") or "").strip(),
                "clause_type": coerce_contract_clause_type(item.get("clause_type")),
                "short_clause_preview": prev or "—",
                "linked_risks": linked,
            }
        )
    return out


def _build_highlighted_risk_clauses(risks: list[dict[str, Any]]) -> list[HighlightedRiskClause]:
    """结构化风险条款卡片（与结构化层 risks 顺序一致，最多 20 条。"""
    out: list[HighlightedRiskClause] = []
    for r in risks[:20]:
        rc = r.get("risk_category")
        rcode = r.get("risk_code")
        out.append(
            cast(
                HighlightedRiskClause,
                {
                    "risk_title": str(r.get("title") or r.get("rule_id") or "—").strip() or "—",
                    "severity": str(r.get("severity") or "medium").strip().lower() or "medium",
                    "matched_text": str(r.get("matched_text") or "").strip(),
                    "location_hint": str(r.get("location_hint") or "").strip(),
                    "short_advice": _short_advice_from_risk(r),
                    "risk_category": coerce_contract_risk_category(
                        str(rc).strip() if rc is not None else None
                    ),
                    "risk_code": (
                        str(rcode).strip()
                        if rcode is not None and str(rcode).strip()
                        else str(r.get("rule_id") or "general").strip() or "general"
                    ),
                },
            )
        )
    return out


def _build_overall_conclusion(
    risks: list[dict[str, Any]],
    missing_items: list[str],
) -> str:
    """按风险强度与缺失规模给出三档总体结论文案。"""
    hi, md, _ = _severity_bucket(risks)
    n_risk = len(risks)
    n_miss = len(missing_items)
    loc = _has_locatable_risk_text(risks)

    if hi >= 1:
        if loc:
            return (
                "合同存在明显高风险内容；规则已在正文中定位到相关条款原文（见 highlighted_risk_clauses）。"
                "建议逐条核对、要求书面澄清或寻求专业意见后再签署。"
            )
        return "合同存在明显高风险内容，建议先修改或寻求专业确认。"
    if md >= 2 or n_risk >= 3:
        return "合同存在若干风险条款，建议谨慎签署。"
    if md >= 1 or n_risk >= 2:
        return "合同存在若干风险条款，建议谨慎签署。"
    if n_risk == 1:
        return "合同整体较安全，但有少量需确认项。"
    # 无规则命中风险
    if n_miss >= 10:
        return "暂未发现规则命中的风险项，但合同中大量常见主题未在正文出现关键词，请核对是否另有附件或需补充条款。"
    if n_miss >= 5:
        return "合同整体较安全，但有少量需确认项；部分常见主题未在文中体现，建议对照标准合同检查。"
    return "合同整体较安全，但有少量需确认项。"


def _build_key_risk_summary(risks: list[dict[str, Any]]) -> str:
    if not risks:
        return "本次规则扫描未发现需要特别标注的高/中风险条款（仍不排除未覆盖的表述）。"
    hi, _, _ = _severity_bucket(risks)
    loc = _has_locatable_risk_text(risks)
    prefix = ""
    if hi >= 1 and loc:
        prefix = "合同中已有明确可定位的高风险条款原文（逐条见下方「highlighted_risk_clauses」）。"
    elif loc:
        prefix = "下列风险均在合同中有原文定位提示，便于在纸质/PDF 中检索核对。"
    lines: list[str] = []
    for r in risks[:6]:
        title = str(r.get("title") or "风险项").strip()
        sev = str(r.get("severity") or "").lower()
        sev_zh = {"high": "高", "medium": "中", "low": "低"}.get(sev, sev or "—")
        mt = str(r.get("matched_text") or "").strip()
        if len(mt) > 72:
            mt = mt[:69] + "…"
        frag = f" — 原文摘录：{mt}" if mt else ""
        lines.append(f"「{title}」（严重度：{sev_zh}）{frag}")
    tail = ""
    if len(risks) > 6:
        tail = f" 另有 {len(risks) - 6} 条未逐条展开。"
    body = "核心风险点包括：" + "；".join(lines) + "。" + tail
    return (prefix + body) if prefix else body


def _build_missing_clause_summary(
    missing_items: list[str],
    detected_topics: list[str],
) -> str:
    if not missing_items:
        return (
            f"在基础关键词层面，常见主题大多有涉及（已识别约 {len(detected_topics)} 类主题表述）。"
            "仍建议通读全文核对数字与附件。"
        )
    head = f"以下 {len(missing_items)} 类主题在正文中未匹配到预设关键词（可能写在附件、表格或未使用常见英文术语）："
    sample = missing_items[:5]
    body = " ".join(f"{i + 1}) {s}" for i, s in enumerate(sample))
    if len(missing_items) > 5:
        body += f" …等共 {len(missing_items)} 项。"
    return head + " " + body


def _build_action_advice(
    risks: list[dict[str, Any]],
    missing_items: list[str],
    recommendations: list[str],
) -> list[str]:
    """输出 3～5 条可执行短句；优先复用分析器 recommendations，再补模板。"""
    out: list[str] = []
    for x in recommendations:
        t = (x or "").strip()
        if t and t not in out:
            out.append(t)

    hi, md, _ = _severity_bucket(risks)
    if hi >= 1 and not any("专业" in x or "律师" in x for x in out[:3]):
        out.insert(
            0,
            "对标记为「高」的风险项，建议拍照/存档并与出租方书面澄清后再签字。",
        )

    if len(missing_items) >= 5:
        tip = "请向中介或房东索要标准条款补充页，重点核对押金托管、涨租与解约通知。"
        if tip not in out:
            out.append(tip)

    if len(out) > 5:
        out = out[:5]
    while len(out) < 3:
        out.append("保留所有沟通记录与合同终稿 PDF，便于日后核对。")
        if len(out) >= 3:
            break
    return out[:5]


def explain_contract_analysis(result: dict[str, Any]) -> ContractExplainResult:
    """
    将 ``analyze_contract_text`` 返回的 dict 转为 Explain 层结构。

    入参 ``result`` 须包含（至少）：risks, missing_items, recommendations；
    可选：summary, detected_topics。

    返回字段：
    - overall_conclusion
    - key_risk_summary
    - missing_clause_summary
    - action_advice（3～5 条 str）
    - highlighted_risk_clauses：可定位风险条款卡片列表（risk_title / severity / matched_text / …）
    - risk_category_groups：按类分组后的 ``risks`` 列表（与结构化层引用一致）
    - risk_category_summary：按类的 count / highest_severity / short_summary
    - clause_overview：条款清单（clause_id / clause_type / short_clause_preview / matched_keywords）
    - clause_risk_overview：按条款聚合的风险挂接（clause_id / clause_type / short_clause_preview / linked_risks）
    - clause_severity_overview：条款风险强度排序列表（与 ``clause_severity_summary`` 对齐，供 Top risky clauses）
    """
    if not isinstance(result, dict):
        result = {}

    risks = _as_risk_list(result.get("risks"))
    missing = _as_str_list(result.get("missing_items"))
    recs = _as_str_list(result.get("recommendations"))
    detected = _as_str_list(result.get("detected_topics"))
    summary_line = str(result.get("summary") or "")

    # 空合同 / 无正文
    if missing == ["合同正文"] or ("未提供合同" in summary_line and "无法分析" in summary_line):
        return cast(
            ContractExplainResult,
            _normalize_explain_out(
                {
                    "overall_conclusion": "未提供有效合同正文，无法形成结论。",
                    "key_risk_summary": "暂无风险项可供说明。",
                    "missing_clause_summary": "请先上传或粘贴完整合同文本后再分析。",
                    "action_advice": [
                        "在租房平台或邮箱中下载带双方信息的合同终稿。",
                        "粘贴全文或导出为文本后再运行分析。",
                        "若只有扫描件，可先使用项目内 PDF 抽取流程获取文字。",
                    ],
                    "highlighted_risk_clauses": [],
                    "risk_category_groups": [],
                    "risk_category_summary": [],
                    "clause_overview": [],
                    "clause_risk_overview": [],
                    "clause_severity_overview": [],
                }
            ),
        )

    hrc = _build_highlighted_risk_clauses(risks)
    raw_groups = result.get("risk_category_groups")
    raw_summary = result.get("risk_category_summary")
    if not isinstance(raw_groups, list):
        raw_groups = group_risks_by_category(risks)
    if not isinstance(raw_summary, list):
        raw_summary = build_risk_category_summary(risks)

    raw_clauses = _as_clause_list(result.get("clause_list"))
    clause_ov = _build_clause_overview(raw_clauses)
    raw_crm = _as_clause_list(result.get("clause_risk_map"))
    clause_risk_ov = _build_clause_risk_overview(raw_clauses, raw_crm, risks)
    raw_css = result.get("clause_severity_summary")
    clause_sev_ov = _normalize_clause_severity_overview(raw_css)

    return cast(
        ContractExplainResult,
        _normalize_explain_out(
            {
                "overall_conclusion": _build_overall_conclusion(risks, missing),
                "key_risk_summary": _build_key_risk_summary(risks),
                "missing_clause_summary": _build_missing_clause_summary(missing, detected),
                "action_advice": _build_action_advice(risks, missing, recs),
                "highlighted_risk_clauses": hrc,
                "risk_category_groups": raw_groups,
                "risk_category_summary": raw_summary,
                "clause_overview": clause_ov,
                "clause_risk_overview": clause_risk_ov,
                "clause_severity_overview": clause_sev_ov,
            }
        ),
    )


# 与部分代码库命名习惯兼容（别名）
format_contract_analysis_output = explain_contract_analysis
