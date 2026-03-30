"""
Phase 3 合同分析：主分析入口（骨架）。
复杂规则与 B 阶段管线后续接入，此处仅返回固定结构。
"""

from __future__ import annotations

from typing import Any

from .contract_models import ContractInput


def analyze_contract_text(contract_input: ContractInput) -> dict[str, Any]:
    """
    对合同文本做占位分析，返回统一结构。

    返回字段至少包含：summary, risks, missing_items, recommendations。
    """
    text = (contract_input.contract_text or "").strip()
    if not text:
        return {
            "summary": "未提供合同文本，无法分析。",
            "risks": [],
            "missing_items": ["合同正文"],
            "recommendations": ["请上传或粘贴完整合同文本后再试。"],
        }

    return {
        "summary": "合同分析模块已就绪（Phase 3 Part 1 骨架）；规则引擎尚未接入。",
        "risks": [],
        "missing_items": [],
        "recommendations": ["后续将在此接入规则匹配与完整性检查。"],
    }
