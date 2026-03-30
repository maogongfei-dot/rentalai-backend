"""
Phase 3 合同分析：Explain 输出层 —— 将 ``analyze_contract_text`` 的结构化结果转为人话说明。

风格对齐 RentalAI 常见「结论 + 摘要 + 建议」表述；纯规则拼接，无 LLM。
"""

from __future__ import annotations

from typing import Any


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


def _build_overall_conclusion(
    risks: list[dict[str, Any]],
    missing_items: list[str],
) -> str:
    """按风险强度与缺失规模给出三档总体结论文案。"""
    hi, md, _ = _severity_bucket(risks)
    n_risk = len(risks)
    n_miss = len(missing_items)

    if hi >= 1:
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
    lines: list[str] = []
    for r in risks[:6]:
        title = str(r.get("title") or "风险项").strip()
        sev = str(r.get("severity") or "").lower()
        sev_zh = {"high": "高", "medium": "中", "low": "低"}.get(sev, sev or "—")
        lines.append(f"「{title}」（严重度：{sev_zh}）")
    tail = ""
    if len(risks) > 6:
        tail = f" 另有 {len(risks) - 6} 条未逐条展开。"
    return "核心风险点包括：" + "；".join(lines) + "。" + tail


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


def explain_contract_analysis(result: dict[str, Any]) -> dict[str, Any]:
    """
    将 ``analyze_contract_text`` 返回的 dict 转为 Explain 层结构。

    入参 ``result`` 须包含（至少）：risks, missing_items, recommendations；
    可选：summary, detected_topics。

    返回字段：
    - overall_conclusion
    - key_risk_summary
    - missing_clause_summary
    - action_advice（3～5 条 str）
    """
    if not isinstance(result, dict):
        result = {}

    risks = [x for x in (result.get("risks") or []) if isinstance(x, dict)]
    missing = [str(x).strip() for x in (result.get("missing_items") or []) if str(x).strip()]
    recs = [str(x).strip() for x in (result.get("recommendations") or []) if str(x).strip()]
    detected = [str(x).strip() for x in (result.get("detected_topics") or []) if str(x).strip()]
    summary_line = str(result.get("summary") or "")

    # 空合同 / 无正文
    if missing == ["合同正文"] or ("未提供合同" in summary_line and "无法分析" in summary_line):
        return {
            "overall_conclusion": "未提供有效合同正文，无法形成结论。",
            "key_risk_summary": "暂无风险项可供说明。",
            "missing_clause_summary": "请先上传或粘贴完整合同文本后再分析。",
            "action_advice": [
                "在租房平台或邮箱中下载带双方信息的合同终稿。",
                "粘贴全文或导出为文本后再运行分析。",
                "若只有扫描件，可先使用项目内 PDF 抽取流程获取文字。",
            ],
        }

    return {
        "overall_conclusion": _build_overall_conclusion(risks, missing),
        "key_risk_summary": _build_key_risk_summary(risks),
        "missing_clause_summary": _build_missing_clause_summary(missing, detected),
        "action_advice": _build_action_advice(risks, missing, recs),
    }


# 与部分代码库命名习惯兼容（别名）
format_contract_analysis_output = explain_contract_analysis
