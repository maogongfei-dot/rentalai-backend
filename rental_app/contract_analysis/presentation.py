"""
Phase 3 合同分析：展示层 —— 将「结构化分析 + explain」整理为产品化输出（CLI 纯文本 / API 分段结构）。

与房源侧 ``explain_engine`` 分段标题风格对齐：结论优先、条列清晰。
Part 5：第二层 CLI 采用英文分段标题（Overall Conclusion / Key Risk Summary / …），与 API ``sections[].title_en`` 对齐。
"""

from __future__ import annotations

from typing import Any

_CLI_SEP = "────────────────────────────"
_HRC_CLI_MAX = 20

# 与 ``contract_analyzer._RCS_SUMMARY_LABEL_ZH`` 一致（CLI / presentation 展示用）
_CATEGORY_LABEL_ZH: dict[str, str] = {
    "deposit": "押金与托管",
    "fees": "费用与收费",
    "access": "进入 / 查看权",
    "repairs": "维修责任",
    "notice": "通知期",
    "rent_increase": "涨租",
    "termination": "解约 / 终止",
    "bills": "账单与 utilities",
    "pets": "宠物政策",
    "subletting": "转租",
    "inventory": "房屋清单",
    "general": "其他 / 未归类",
}


def _category_title_zh(code: str) -> str:
    c = (code or "general").strip().lower()
    return _CATEGORY_LABEL_ZH.get(c, c)


def _risk_rows_from_explain_layers(
    ex: dict[str, Any], sa: dict[str, Any], key: str
) -> list[dict[str, Any]]:
    raw = ex.get(key)
    if not isinstance(raw, list) or not raw:
        raw = sa.get(key)
    if not isinstance(raw, list):
        return []
    return [x for x in raw if isinstance(x, dict)]


def _risk_titles_from_group(group: dict[str, Any]) -> list[str]:
    rs = group.get("risks")
    if not isinstance(rs, list):
        return []
    out: list[str] = []
    for r in rs:
        if not isinstance(r, dict):
            continue
        t = str(r.get("title") or r.get("rule_id") or "").strip()
        if t:
            out.append(t)
    return out


def _enrich_risk_category_groups_for_api(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """在 presentation 的 section items 上附加 ``risk_titles``，便于前端无需再从 ``risks`` 拆解标题。"""
    enriched: list[dict[str, Any]] = []
    for g in items:
        d = dict(g)
        d["risk_titles"] = _risk_titles_from_group(g)
        enriched.append(d)
    return enriched


def format_contract_analysis_cli_report(
    structured_analysis: dict[str, Any],
    explain: dict[str, Any],
) -> str:
    """
    生成适合终端阅读的纯文本报告（两层：结构化摘要 + 人话解读）。

    第二层按固定顺序分段：Overall Conclusion → Key Risk Summary → Risk Category Summary →
    Risk Category Groups → Highlighted Risk Clauses → Missing Clause Summary → Action Advice。
    """
    sa = structured_analysis if isinstance(structured_analysis, dict) else {}
    ex = explain if isinstance(explain, dict) else {}

    risks = sa.get("risks") or []
    topics = sa.get("detected_topics") or []
    missing = sa.get("missing_items") or []
    hrc_raw = ex.get("highlighted_risk_clauses") or []
    hrc: list[dict[str, Any]] = [x for x in hrc_raw if isinstance(x, dict)]

    lines: list[str] = [
        "===== RentalAI 合同分析 · Phase 3 =====",
        "",
        "【第一层】结构化分析",
        _CLI_SEP,
        sa.get("summary") or "（无摘要）",
        "",
        f"· 规则命中风险：{len(risks)} 条",
        f"· 正文覆盖主题：{len(topics)} 类",
        f"· 未匹配主题项：{len(missing)} 类",
        "",
    ]
    if isinstance(risks, list) and risks:
        lines.append("· 风险条目（规则层 · 原文摘录 / 定位提示）")
        for i, r in enumerate(risks[:8], start=1):
            if not isinstance(r, dict):
                continue
            title = str(r.get("title") or "").strip() or "（未命名风险）"
            mt = str(r.get("matched_text") or "").strip()
            lh = str(r.get("location_hint") or "").strip()
            if len(mt) > 140:
                mt = mt[:137] + "…"
            lines.append(f"  {i}. {title}")
            if mt:
                lines.append(f"     matched_text: {mt}")
            if lh:
                lines.append(f"     location_hint: {lh}")
        if len(risks) > 8:
            lines.append(f"  … 另有 {len(risks) - 8} 条见 structured_analysis.risks / JSON。")
        lines.append("")

    lines.extend(
        [
            "【第二层】人话解读（Explain）",
            _CLI_SEP,
            "",
            "Overall Conclusion",
            _CLI_SEP,
            ex.get("overall_conclusion") or "—",
            "",
            "Key Risk Summary",
            _CLI_SEP,
            ex.get("key_risk_summary") or "—",
            "",
            "Risk Category Summary",
            _CLI_SEP,
        ]
    )
    rc_summary_rows = _risk_rows_from_explain_layers(ex, sa, "risk_category_summary")
    if rc_summary_rows:
        for row in rc_summary_rows:
            cat = str(row.get("category") or "general").strip() or "general"
            cat_zh = _category_title_zh(cat)
            try:
                cnt = int(row.get("count", 0))
            except (TypeError, ValueError):
                cnt = 0
            hsev = str(row.get("highest_severity") or "—").strip() or "—"
            summ = str(row.get("short_summary") or "").strip()
            lines.append(f"  · {cat_zh} ({cat})")
            lines.append(f"      count: {cnt}")
            lines.append(f"      highest_severity: {hsev}")
            if summ:
                lines.append(f"      short_summary: {summ}")
            lines.append("")
    else:
        lines.append("  (none — no risks or no category rollup.)")
        lines.append("")

    lines.extend(
        [
            "Risk Category Groups",
            _CLI_SEP,
        ]
    )
    rc_group_rows = _risk_rows_from_explain_layers(ex, sa, "risk_category_groups")
    if rc_group_rows:
        for g in rc_group_rows:
            cat = str(g.get("category") or "general").strip() or "general"
            cat_zh = _category_title_zh(cat)
            titles = _risk_titles_from_group(g)
            lines.append(f"  【{cat_zh}】 ({cat})")
            if titles:
                for t in titles:
                    lines.append(f"    - {t}")
            else:
                lines.append("    - （无标题）")
            lines.append("")
    else:
        lines.append("  (none — no risks grouped by type.)")
        lines.append("")

    lines.extend(
        [
            "Highlighted Risk Clauses",
            _CLI_SEP,
        ]
    )
    if hrc:
        for i, card in enumerate(hrc[:_HRC_CLI_MAX], start=1):
            rt = str(card.get("risk_title") or "").strip() or "—"
            sev = str(card.get("severity") or "").strip() or "—"
            mt = str(card.get("matched_text") or "").strip() or "—"
            lh = str(card.get("location_hint") or "").strip() or "—"
            sa_card = str(card.get("short_advice") or "").strip() or "—"
            if len(mt) > 220:
                mt = mt[:217] + "…"
            lines.append(f"  [{i}] {rt}  [severity: {sev}]")
            lines.append(f"      matched_text: {mt}")
            lines.append(f"      location_hint: {lh}")
            lines.append(f"      short_advice: {sa_card}")
            lines.append("")
        if len(hrc) > _HRC_CLI_MAX:
            lines.append(f"  … {_HRC_CLI_MAX}+ 条见 explain.highlighted_risk_clauses（共 {len(hrc)} 条）。")
            lines.append("")
    else:
        lines.append("  (none — no explain-level clause cards; see structured risks above if any.)")
        lines.append("")

    lines.extend(
        [
            "Missing Clause Summary",
            _CLI_SEP,
            ex.get("missing_clause_summary") or "—",
            "",
            "Action Advice",
            _CLI_SEP,
        ]
    )
    adv = ex.get("action_advice") or []
    if isinstance(adv, list) and adv:
        for i, a in enumerate(adv, start=1):
            lines.append(f"  {i}. {a}")
    else:
        lines.append("  —")
    lines.append("")
    lines.append(_CLI_SEP)
    lines.append("说明：本报告由规则与关键词生成，不构成法律意见。")
    return "\n".join(lines)


def build_contract_presentation(
    structured_analysis: dict[str, Any],
    explain: dict[str, Any],
) -> dict[str, Any]:
    """
    供 API / 前端使用的「产品化」分段结构（与 explain 字段一致，便于直接渲染卡片）。

    返回字段：
    - product_title / phase / decision_style（与 RentalAI decision 块命名习惯对齐）
    - sections：分段标题 + ``title_en``（英文键名，便于 UI）+ kind / text 或 items
    - plain_text：与 CLI 一致的完整可读文本

    ``sections`` 中 ``risk_category_summary`` 的 ``items`` 为汇总行（category / count /
    highest_severity / short_summary）；``risk_category_groups`` 的 ``items`` 在每条上含原有
    ``category``、``risks``，并附加 ``risk_titles``（标题列表，便于前端直接渲染）。
    ``highlighted_risk_clauses`` 的 ``items`` 为 ``HighlightedRiskClause`` 字典列表，
    每条含 risk_title / severity / matched_text / location_hint / short_advice / risk_category / risk_code。
    """
    ex = explain if isinstance(explain, dict) else {}
    sa = structured_analysis if isinstance(structured_analysis, dict) else {}

    hrc_items = [x for x in (ex.get("highlighted_risk_clauses") or []) if isinstance(x, dict)]
    rc_summary_items = [x for x in (ex.get("risk_category_summary") or []) if isinstance(x, dict)]
    if not rc_summary_items:
        rc_summary_items = [x for x in (sa.get("risk_category_summary") or []) if isinstance(x, dict)]
    rc_group_items = [x for x in (ex.get("risk_category_groups") or []) if isinstance(x, dict)]
    if not rc_group_items:
        rc_group_items = [x for x in (sa.get("risk_category_groups") or []) if isinstance(x, dict)]
    rc_group_items_api = _enrich_risk_category_groups_for_api(rc_group_items)

    sections: list[dict[str, Any]] = [
        {
            "id": "overall_conclusion",
            "title": "总体结论",
            "title_en": "Overall Conclusion",
            "kind": "text",
            "text": str(ex.get("overall_conclusion") or ""),
        },
        {
            "id": "key_risk_summary",
            "title": "核心风险摘要",
            "title_en": "Key Risk Summary",
            "kind": "text",
            "text": str(ex.get("key_risk_summary") or ""),
        },
        {
            "id": "risk_category_summary",
            "title": "风险类型汇总",
            "title_en": "Risk Category Summary",
            "kind": "risk_category_summary",
            "items": rc_summary_items,
        },
        {
            "id": "risk_category_groups",
            "title": "风险类型分组",
            "title_en": "Risk Category Groups",
            "kind": "risk_category_groups",
            "items": rc_group_items_api,
        },
        {
            "id": "highlighted_risk_clauses",
            "title": "风险条款原文（可定位）",
            "title_en": "Highlighted Risk Clauses",
            "kind": "risk_clauses",
            "items": hrc_items,
        },
        {
            "id": "missing_clause_summary",
            "title": "缺失条款摘要",
            "title_en": "Missing Clause Summary",
            "kind": "text",
            "text": str(ex.get("missing_clause_summary") or ""),
        },
        {
            "id": "action_advice",
            "title": "建议下一步",
            "title_en": "Action Advice",
            "kind": "bullets",
            "items": [str(x) for x in (ex.get("action_advice") or []) if str(x).strip()],
        },
    ]

    plain = format_contract_analysis_cli_report(sa, ex)

    return {
        "product_title": "RentalAI 合同分析报告",
        "phase": "phase3_contract",
        "decision_style": "contract_analysis_v1",
        "layers": {
            "structured_analysis": "第一层 · 规则与主题扫描结果",
            "explain": "第二层 · 人话解读与行动建议",
        },
        "sections": sections,
        "plain_text": plain,
    }


def normalize_phase3_result(result: dict[str, Any]) -> dict[str, Any]:
    """
    兼容旧版「扁平 + explain」结构：若缺少 structured_analysis，则从扁平字段组装。
    """
    if not isinstance(result, dict):
        return {}
    if "structured_analysis" in result and isinstance(result.get("structured_analysis"), dict):
        return result
    if "explain" in result and "summary" in result:
        base = {k: v for k, v in result.items() if k != "explain"}
        return {
            "structured_analysis": base,
            "explain": result.get("explain") or {},
        }
    return result
