"""
Phase 3 合同分析：展示层 —— 将「结构化分析 + explain」整理为产品化输出（CLI 纯文本 / API 分段结构）。

与房源侧 ``explain_engine`` 分段标题风格对齐：结论优先、条列清晰。
"""

from __future__ import annotations

from typing import Any


def format_contract_analysis_cli_report(
    structured_analysis: dict[str, Any],
    explain: dict[str, Any],
) -> str:
    """
    生成适合终端阅读的纯文本报告（两层：结构化摘要 + 人话解读）。
    """
    sa = structured_analysis if isinstance(structured_analysis, dict) else {}
    ex = explain if isinstance(explain, dict) else {}

    risks = sa.get("risks") or []
    topics = sa.get("detected_topics") or []
    missing = sa.get("missing_items") or []

    lines: list[str] = [
        "===== RentalAI 合同分析 · Phase 3 =====",
        "",
        "【第一层】结构化分析",
        "────────────────────────────",
        sa.get("summary") or "（无摘要）",
        "",
        f"· 规则命中风险：{len(risks)} 条",
        f"· 正文覆盖主题：{len(topics)} 类",
        f"· 未匹配主题项：{len(missing)} 类",
        "",
    ]
    if isinstance(risks, list) and risks:
        lines.append("· 风险条目（原文摘录 / 定位提示）")
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
                lines.append(f"     摘录：{mt}")
            if lh:
                lines.append(f"     定位：{lh}")
        if len(risks) > 8:
            lines.append(f"  … 另有 {len(risks) - 8} 条见 JSON / API。")
        lines.append("")
    lines.extend(
        [
            "【第二层】人话解读",
            "────────────────────────────",
            "■ 总体结论",
            ex.get("overall_conclusion") or "—",
            "",
            "■ 核心风险摘要",
            ex.get("key_risk_summary") or "—",
            "",
            "■ 缺失条款摘要",
            ex.get("missing_clause_summary") or "—",
            "",
            "■ 建议下一步",
        ]
    )
    adv = ex.get("action_advice") or []
    if isinstance(adv, list) and adv:
        for i, a in enumerate(adv, start=1):
            lines.append(f"  {i}. {a}")
    else:
        lines.append("  —")
    lines.append("")
    lines.append("────────────────────────────")
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
    - sections：分段标题 + 文本或列表
    - plain_text：与 CLI 一致的完整可读文本
    """
    ex = explain if isinstance(explain, dict) else {}
    sa = structured_analysis if isinstance(structured_analysis, dict) else {}

    sections: list[dict[str, Any]] = [
        {
            "id": "overall_conclusion",
            "title": "总体结论",
            "kind": "text",
            "text": str(ex.get("overall_conclusion") or ""),
        },
        {
            "id": "key_risk_summary",
            "title": "核心风险摘要",
            "kind": "text",
            "text": str(ex.get("key_risk_summary") or ""),
        },
        {
            "id": "missing_clause_summary",
            "title": "缺失条款摘要",
            "kind": "text",
            "text": str(ex.get("missing_clause_summary") or ""),
        },
        {
            "id": "action_advice",
            "title": "建议下一步",
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
