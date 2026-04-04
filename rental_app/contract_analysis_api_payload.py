"""
Phase 4：合同分析 HTTP 响应体整理（仅组装字段，不修改 analyzer / explainer）。

将 ``contract_analysis_service`` 门面结果拆为：
- **summary_view**：供列表页 / 首屏直接绑定的 explain 核心字段；
- **raw_analysis**：完整 ``analysis_result`` / ``explain_result`` / ``presentation``，供展开与调试。
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from contract_analysis_service import ContractAnalysisFacadeResult


def build_contract_analysis_ui_payload(facade: ContractAnalysisFacadeResult) -> dict[str, Any]:
    """
    从门面结果生成 ``result`` 对象（含 ``summary_view`` + ``raw_analysis``）。

    ``summary_view`` 字段稳定：list 永为 list，``contract_completeness_overview`` 永为 dict。
    """
    er = facade["explain_result"]
    if not isinstance(er, dict):
        er = {}
    ar = facade["analysis_result"]
    pr = facade.get("presentation")

    def _list(key: str) -> list[Any]:
        v = er.get(key)
        return v if isinstance(v, list) else []

    def _dict_cco(key: str) -> dict[str, Any]:
        v = er.get(key)
        return v if isinstance(v, dict) else {}

    summary_view: dict[str, Any] = {
        "overall_conclusion": str(er.get("overall_conclusion") or "").strip(),
        "key_risk_summary": str(er.get("key_risk_summary") or "").strip(),
        "risk_category_summary": _list("risk_category_summary"),
        "highlighted_risk_clauses": _list("highlighted_risk_clauses"),
        "clause_severity_overview": _list("clause_severity_overview"),
        "contract_completeness_overview": _dict_cco("contract_completeness_overview"),
        "action_advice": _list("action_advice"),
    }

    out: dict[str, Any] = {
        "summary_view": summary_view,
        "raw_analysis": {
            "analysis_result": ar,
            "explain_result": er,
            "presentation": pr,
        },
    }
    try:
        _repo_root = Path(__file__).resolve().parents[1]
        if str(_repo_root) not in sys.path:
            sys.path.insert(0, str(_repo_root))
        from backend.app.legal.legal_integration import attach_legal_compliance_to_result

        result = attach_legal_compliance_to_result(
            {
                "analysis_result": ar,
                "explain_result": er,
                "presentation": pr,
            },
            jurisdiction="england",
            target_date=None,
            source_type="contract_clause",
        )
        if result.get("legal_compliance") is not None:
            out["legal_compliance"] = result["legal_compliance"]
    except Exception as e:
        print("LEGAL INTEGRATION ERROR:", e)
        lc = facade.get("legal_compliance")
        if lc is not None:
            out["legal_compliance"] = lc
    return out
