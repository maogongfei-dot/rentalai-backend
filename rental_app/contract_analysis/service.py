"""
Phase 3 合同分析：对外服务包装（供 API / CLI 调用，与 MVP 房源流程隔离）。

开发说明（输入/输出/限制/Phase 4 接入）：见同目录 ``README.md``。

支持：
- 纯文本：``analyze_contract`` / ``analyze_contract_with_explain``（``contract_text``）。
- 文件路径：``build_contract_input_from_file``、``analyze_contract_file``、
  ``analyze_contract_file_with_explain``（``file_path`` → 提取 → 分析 → explain）。

Phase 4 建议优先复用：``analyze_contract_with_explain``（或文件版 ``analyze_contract_file_with_explain``），与 ``api_server`` 中 Phase 3 路由一致。
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import cast

from .contract_analyzer import analyze_contract_text as _analyze_contract_text
from .contract_document_reader import (
    extract_contract_text_outcome,
    infer_contract_source_type_from_path,
)
from .contract_explainer import explain_contract_analysis
from .contract_models import (
    ContractAnalysisResult,
    ContractInput,
    ContractPhase3PipelineResult,
    coerce_contract_source_type,
)
from .presentation import build_contract_presentation


def analyze_contract(
    *,
    contract_text: str,
    monthly_rent: float | None = None,
    deposit_amount: float | None = None,
    fixed_term_months: int | None = None,
    source_type: str = "text",
    source_name: str | None = None,
) -> ContractAnalysisResult:
    """
    合同分析统一入口：返回 ``ContractAnalysisResult`` 形状（含 ``meta``）。

    与根目录 ``contract_text_analyzer``（Phase B）区分：本函数仅走 ``contract_analysis`` 规则引擎。
    """
    inp = ContractInput(
        contract_text=contract_text or "",
        monthly_rent=monthly_rent,
        deposit_amount=deposit_amount,
        fixed_term_months=fixed_term_months,
        source_type=coerce_contract_source_type(source_type),
        source_name=source_name,
    )
    return _analyze_contract_text(inp)


def analyze_contract_with_explain(
    *,
    contract_text: str,
    monthly_rent: float | None = None,
    deposit_amount: float | None = None,
    fixed_term_months: int | None = None,
    source_type: str = "text",
    source_name: str | None = None,
) -> ContractPhase3PipelineResult:
    """
    完整 Phase 3 输出（两层 + 展示层），形状见 ``ContractPhase3PipelineResult``。
    **推荐作为非 HTTP 调用的统一入口**（上传/任务队列封装时直接调用本函数）。

    - ``structured_analysis``：第一层（含 ``meta``、``risks[].matched_text``、``clause_risk_map``、``clause_severity_summary``、``contract_completeness``（``build_contract_completeness``）等）。
    - ``explain``：第二层（含 ``highlighted_risk_clauses``、``clause_risk_overview``、``clause_severity_overview``、``contract_completeness_overview`` 等，与 CLI/API 展示对齐）。
    - ``presentation``：``sections``（含 ``kind=contract_completeness_overview`` 单卡、``kind=clause_severity_overview`` 的 ``items``、与 CLI 一致的 ``plain_text`` 等；``plain_text`` 含 Contract Completeness Check / Clause Severity Overview 分段）。
    """
    base = analyze_contract(
        contract_text=contract_text,
        monthly_rent=monthly_rent,
        deposit_amount=deposit_amount,
        fixed_term_months=fixed_term_months,
        source_type=source_type,
        source_name=source_name,
    )
    ex = explain_contract_analysis(base)
    pres = build_contract_presentation(base, ex)
    return cast(
        ContractPhase3PipelineResult,
        {
            "structured_analysis": base,
            "explain": ex,
            "presentation": pres,
        },
    )


def build_contract_input_from_file(
    file_path: str | os.PathLike[str],
    *,
    monthly_rent: float | None = None,
    deposit_amount: float | None = None,
    fixed_term_months: int | None = None,
    source_type: str | None = None,
) -> ContractInput:
    """
    从 ``txt`` / ``pdf`` / ``docx`` 路径提取正文并构造 ``ContractInput``。

    ``source_type`` 为 ``None`` 时按扩展名推断；否则在提取时按传入类型选择读取器（须与文件实际格式一致）。

    提取失败时抛出 ``ValueError``，信息来自读取层（库缺失、空文件、无文本层等）。
    """
    path = Path(file_path).expanduser()
    out = extract_contract_text_outcome(path, source_type=source_type)
    err = out.get("error")
    if err:
        raise ValueError(err)
    text = out.get("text") or ""
    if source_type is None:
        st = infer_contract_source_type_from_path(path)
    else:
        st = coerce_contract_source_type(source_type)
        if st == "text":
            st = "txt"
    return ContractInput(
        contract_text=text,
        monthly_rent=monthly_rent,
        deposit_amount=deposit_amount,
        fixed_term_months=fixed_term_months,
        source_type=st,
        source_name=path.name,
    )


def analyze_contract_file(
    *,
    file_path: str | os.PathLike[str],
    monthly_rent: float | None = None,
    deposit_amount: float | None = None,
    fixed_term_months: int | None = None,
    source_type: str | None = None,
) -> ContractAnalysisResult:
    """文件 → 结构化分析（第一层）。"""
    inp = build_contract_input_from_file(
        file_path,
        monthly_rent=monthly_rent,
        deposit_amount=deposit_amount,
        fixed_term_months=fixed_term_months,
        source_type=source_type,
    )
    return _analyze_contract_text(inp)


def analyze_contract_file_with_explain(
    *,
    file_path: str | os.PathLike[str],
    monthly_rent: float | None = None,
    deposit_amount: float | None = None,
    fixed_term_months: int | None = None,
    source_type: str | None = None,
) -> ContractPhase3PipelineResult:
    """文件 → 提取 → 结构化分析 → explain → 展示层（与 ``analyze_contract_with_explain`` 同形）。"""
    inp = build_contract_input_from_file(
        file_path,
        monthly_rent=monthly_rent,
        deposit_amount=deposit_amount,
        fixed_term_months=fixed_term_months,
        source_type=source_type,
    )
    base = _analyze_contract_text(inp)
    ex = explain_contract_analysis(base)
    pres = build_contract_presentation(base, ex)
    return cast(
        ContractPhase3PipelineResult,
        {
            "structured_analysis": base,
            "explain": ex,
            "presentation": pres,
        },
    )
