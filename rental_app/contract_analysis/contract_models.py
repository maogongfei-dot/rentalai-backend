"""
Phase 3 合同分析：输入与输出数据结构（TypedDict + dataclass，与 ``contract_analyzer`` / ``contract_explainer`` 一致）。

下一阶段文档读取（PDF/DOCX/TXT）预留：``ContractInput.source_type`` / ``source_name``，
分析结果通过 ``ContractAnalysisResult.meta`` 回显，便于审计与前端展示。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Optional, TypedDict, cast

# --- 来源类型（与 ``contract_document_reader`` / API 对齐）---
# text：粘贴或内存中的正文；txt：自 .txt 文件读取；pdf / docx：自对应文件抽取。
ContractSourceType = Literal["text", "txt", "pdf", "docx"]

# Phase 6：风险条款分类（与 ``contract_rules`` / ``highlighted_risk_clauses`` 对齐）
ContractRiskCategory = Literal[
    "deposit",
    "fees",
    "access",
    "repairs",
    "notice",
    "rent_increase",
    "termination",
    "bills",
    "pets",
    "subletting",
    "inventory",
    "general",
]

_CONTRACT_RISK_CATEGORY_VALUES = frozenset(
    {
        "deposit",
        "fees",
        "access",
        "repairs",
        "notice",
        "rent_increase",
        "termination",
        "bills",
        "pets",
        "subletting",
        "inventory",
        "general",
    }
)


def coerce_contract_source_type(raw: str | None) -> ContractSourceType:
    """将 API / CLI 传入的字符串规范为 ``ContractSourceType``（未知值回退为 ``text``）。"""
    r = (raw or "text").strip().lower()
    if r in ("text", "txt", "pdf", "docx"):
        return cast(ContractSourceType, r)
    return "text"


def coerce_contract_risk_category(raw: str | None) -> str:
    """将任意字符串规范为 ``ContractRiskCategory``；未知值回退为 ``general``。"""
    r = (raw or "general").strip().lower()
    if r in _CONTRACT_RISK_CATEGORY_VALUES:
        return r
    return "general"


# Part 7：条款级结构（clause 切分 / clause_type 识别预留；与风险层 ``risk_category`` 独立）
ContractClauseType = Literal[
    "deposit",
    "rent",
    "notice",
    "repairs",
    "bills",
    "access",
    "termination",
    "rent_increase",
    "inventory",
    "pets",
    "subletting",
    "general",
]

_CONTRACT_CLAUSE_TYPE_VALUES = frozenset(
    {
        "deposit",
        "rent",
        "notice",
        "repairs",
        "bills",
        "access",
        "termination",
        "rent_increase",
        "inventory",
        "pets",
        "subletting",
        "general",
    }
)


def coerce_contract_clause_type(raw: str | None) -> str:
    """将任意字符串规范为 ``ContractClauseType``；未知值回退为 ``general``。"""
    r = (raw or "general").strip().lower()
    if r in _CONTRACT_CLAUSE_TYPE_VALUES:
        return r
    return "general"


@dataclass
class ContractInput:
    """
    合同分析入口入参。

    必填语义字段：
    - ``contract_text``：待分析正文（粘贴、或经 ``extract_contract_text`` 等得到的字符串）。
    - ``source_type``：来源类别，见 ``ContractSourceType``。
    - ``source_name``：可选，如原始文件名，写入 ``ContractAnalysisResult.meta`` 便于展示/审计。
    """

    contract_text: str
    monthly_rent: Optional[float] = None
    deposit_amount: Optional[float] = None
    fixed_term_months: Optional[int] = None
    source_type: ContractSourceType = "text"
    source_name: Optional[str] = None


class ContractRiskCategoryGroup(TypedDict, total=False):
    """按 ``risk_category`` 分组后的结构（``risks`` 为与结构化层相同的字典列表）。"""

    category: str
    risks: list[ContractRiskItem]


class ContractRiskCategorySummaryItem(TypedDict, total=False):
    """单类风险的汇总行（供 UI / explain 与第一层对齐）。"""

    category: str
    count: int
    highest_severity: str
    short_summary: str


class ContractRiskItem(TypedDict, total=False):
    """
    单条风险（``ContractAnalysisResult.risks`` 元素）。

    ``matched_text``：原文片段（整行或匹配点附近窗口）；``matched_keyword``：正则匹配字面；
    ``location_hint``：文本级提示（句序号/行号/near clause containing），无 PDF 页码。
    ``risk_category`` / ``risk_code``：条款分类（见 ``ContractRiskCategory``）与稳定短码。
    """

    rule_id: str
    title: str
    severity: str
    reason: str
    matched_text: str
    matched_keyword: str
    location_hint: str
    risk_category: str
    risk_code: str


class ContractClauseOverviewItem(TypedDict, total=False):
    """Explain 层条款清单卡片（截断预览，便于前端列表）。"""

    clause_id: str
    clause_type: str
    short_clause_preview: str
    matched_keywords: list[str]


class ContractClauseItem(TypedDict, total=False):
    """
    单条条款级记录（``ContractAnalysisResult.clause_list`` 元素）。

    ``clause_type``：见 ``ContractClauseType``，由 ``annotate_clause_types`` / ``match_clause_type_from_text`` 填写。
    ``matched_keywords``：命中 ``contract_rules.CLAUSE_TYPE_KEYWORDS`` 中的关键词子串列表。
    ``risk_flags`` 为轻量标签（如后续 rule_id 联动）。
    """

    clause_id: str
    clause_text: str
    clause_type: str
    matched_keywords: list[str]
    risk_flags: list[str]
    location_hint: str


class ClauseRiskLinkItem(TypedDict, total=False):
    """
    单条「条款—风险」联动记录（``ContractAnalysisResult.clause_risk_map`` 元素）。

    与 ``ContractRiskItem`` 区分：显式绑定 ``clause_id``，并附 ``link_reason`` 说明关联依据（规则/重叠文本等）。
    """

    clause_id: str
    risk_title: str
    risk_category: str
    severity: str
    matched_keyword: str
    matched_text: str
    location_hint: str
    link_reason: str


class ClauseSeverityItem(TypedDict, total=False):
    """
    单条条款级风险强度汇总（``ContractAnalysisResult.clause_severity_summary`` 元素）。

    ``severity_score``：条款级强度分，为关联每条 risk 的权重之和（high=3 / medium=2 / low=1）。
    ``highest_severity``：本条条款关联风险中的最高严重度（high / medium / low）。
    ``linked_risk_titles``：关联风险标题列表（与 ``clause_risk_map`` 对齐）。
    ``location_hint``：条款级定位提示，可与 ``ContractClauseItem.location_hint`` 一致。
    """

    clause_id: str
    clause_type: str
    severity_score: int
    highest_severity: str
    linked_risk_count: int
    linked_risk_titles: list[str]
    short_clause_preview: str
    location_hint: str


class ContractAnalysisMeta(TypedDict, total=False):
    """随分析结果回显的来源信息（与 ``ContractInput`` 对应）。"""

    source_type: str
    source_name: str | None


class ContractAnalysisResult(TypedDict, total=False):
    """``analyze_contract_text`` / ``analyze_contract`` 第一层（结构化分析）。"""

    summary: str
    risks: list[ContractRiskItem]
    risk_category_groups: list[ContractRiskCategoryGroup]
    risk_category_summary: list[ContractRiskCategorySummaryItem]
    clause_list: list[ContractClauseItem]
    clause_risk_map: list[ClauseRiskLinkItem]
    clause_severity_summary: list[ClauseSeverityItem]
    missing_items: list[str]
    recommendations: list[str]
    detected_topics: list[str]
    meta: ContractAnalysisMeta


class HighlightedRiskClause(TypedDict, total=False):
    """单条「可定位风险条款」卡片（与 ``explain_contract_analysis`` 的 ``highlighted_risk_clauses`` 元素一致）。"""

    risk_title: str
    severity: str
    matched_text: str
    location_hint: str
    short_advice: str
    risk_category: str
    risk_code: str


class ClauseRiskLinkedRiskBrief(TypedDict, total=False):
    """Explain 层「某条款下挂接的风险」摘要（嵌于 ``clause_risk_overview``）。"""

    risk_title: str
    risk_category: str
    severity: str
    matched_keyword: str
    short_reason: str


class ClauseRiskOverviewItem(TypedDict, total=False):
    """Explain 层条款—风险聚合卡片：一条条款 + 其关联的若干风险摘要。"""

    clause_id: str
    clause_type: str
    short_clause_preview: str
    linked_risks: list[ClauseRiskLinkedRiskBrief]


class ClauseSeverityOverviewItem(TypedDict, total=False):
    """
    Explain 层「优先关注条款」卡片（与结构化 ``clause_severity_summary`` 对齐，供 Top risky clauses）。

    字段与第一层汇总一致，便于前端直接渲染；无关联风险时 explain 为稳定空 list。
    """

    clause_id: str
    clause_type: str
    severity_score: int
    highest_severity: str
    linked_risk_count: int
    short_clause_preview: str
    linked_risk_titles: list[str]


class ContractExplainResult(TypedDict, total=False):
    """``explain_contract_analysis`` 输出（人话层）。"""

    overall_conclusion: str
    key_risk_summary: str
    missing_clause_summary: str
    action_advice: list[str]
    highlighted_risk_clauses: list[HighlightedRiskClause]
    risk_category_groups: list[ContractRiskCategoryGroup]
    risk_category_summary: list[ContractRiskCategorySummaryItem]
    clause_overview: list[ContractClauseOverviewItem]
    clause_risk_overview: list[ClauseRiskOverviewItem]
    clause_severity_overview: list[ClauseSeverityOverviewItem]


# 兼容旧名（Part 2 前使用 ContractExplainBundle）
ContractExplainBundle = ContractExplainResult


class ContractPresentationSection(TypedDict, total=False):
    """``ContractPresentationBundle.sections`` 单项。"""

    id: str
    title: str
    title_en: str
    kind: str
    text: str
    items: list[Any]


class ContractPresentationBundle(TypedDict, total=False):
    """``build_contract_presentation`` 输出（展示层）。"""

    product_title: str
    phase: str
    decision_style: str
    layers: dict[str, str]
    sections: list[dict[str, Any]]
    plain_text: str


class ContractPhase3PipelineResult(TypedDict, total=False):
    """``analyze_contract_with_explain`` 完整返回（结构化 + explain + presentation）。"""

    structured_analysis: ContractAnalysisResult
    explain: ContractExplainResult
    presentation: ContractPresentationBundle
