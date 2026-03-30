"""
Phase 3 合同分析：样例合同演示与最小校验入口。

运行::

    python -m contract_analysis.demo_contract_samples

或在代码中调用 ``run_contract_analysis_demo()``。
"""

from __future__ import annotations

from typing import Any

from .sample_contracts_data import (
    SAMPLE_CONTRACT_DEPOSIT_HEAVY,
    SAMPLE_CONTRACT_HIDDEN_FEES_PENALTY,
    SAMPLE_CONTRACT_HIGH_RISK,
    SAMPLE_CONTRACT_MEDIUM_RISK,
    SAMPLE_CONTRACT_MISSING_NOTICE_REPAIR,
    SAMPLE_CONTRACT_SAFE,
    SAMPLE_CONTRACT_UNFAIR_ENTRY,
    SAMPLE_LOC_HIDDEN_FEE,
    SAMPLE_LOC_LANDLORD_ACCESS,
    SAMPLE_LOC_TENANT_REPAIRS,
)
from .service import analyze_contract_with_explain


def _sample_specs() -> list[tuple[str, str, dict[str, Any]]]:
    """(标签, 全文, analyze_contract_with_explain 可选数值参数)"""
    return [
        (
            "sample_contract_safe",
            SAMPLE_CONTRACT_SAFE,
            {"monthly_rent": 950.0, "deposit_amount": 1095.0},
        ),
        (
            "sample_contract_medium_risk",
            SAMPLE_CONTRACT_MEDIUM_RISK,
            {"monthly_rent": 850.0, "deposit_amount": 850.0},
        ),
        (
            "sample_contract_high_risk",
            SAMPLE_CONTRACT_HIGH_RISK,
            {"monthly_rent": 800.0, "deposit_amount": 2500.0},
        ),
        (
            "sample_contract_deposit_heavy",
            SAMPLE_CONTRACT_DEPOSIT_HEAVY,
            {"monthly_rent": 1000.0, "deposit_amount": 8000.0},
        ),
        (
            "sample_contract_missing_notice_repair",
            SAMPLE_CONTRACT_MISSING_NOTICE_REPAIR,
            {"monthly_rent": 1200.0, "deposit_amount": None},
        ),
        (
            "sample_contract_unfair_entry",
            SAMPLE_CONTRACT_UNFAIR_ENTRY,
            {"monthly_rent": 950.0, "deposit_amount": 950.0},
        ),
        (
            "sample_contract_hidden_fees_penalty",
            SAMPLE_CONTRACT_HIDDEN_FEES_PENALTY,
            {"monthly_rent": 850.0, "deposit_amount": 850.0},
        ),
        (
            "sample_loc_hidden_fee",
            SAMPLE_LOC_HIDDEN_FEE,
            {"monthly_rent": 900.0, "deposit_amount": None},
        ),
        (
            "sample_loc_landlord_access",
            SAMPLE_LOC_LANDLORD_ACCESS,
            {"monthly_rent": 950.0, "deposit_amount": None},
        ),
        (
            "sample_loc_tenant_repairs",
            SAMPLE_LOC_TENANT_REPAIRS,
            {"monthly_rent": 880.0, "deposit_amount": None},
        ),
    ]


def validate_contract_analysis_samples() -> None:
    """断言各样例均能生成完整 explain 与稳定 list 字段（供 pytest 调用）。"""
    for label, text, kwargs in _sample_specs():
        out = analyze_contract_with_explain(contract_text=text, **kwargs)
        assert "structured_analysis" in out and "explain" in out
        sa = out["structured_analysis"]
        ex = out["explain"]
        assert isinstance(sa.get("summary"), str)
        assert isinstance(sa.get("risks"), list)
        assert isinstance(sa.get("missing_items"), list)
        assert isinstance(sa.get("recommendations"), list)
        assert isinstance(sa.get("detected_topics"), list)
        meta = sa.get("meta")
        assert isinstance(meta, dict)
        assert meta.get("source_type") == "text"
        for k in ("overall_conclusion", "key_risk_summary", "missing_clause_summary"):
            assert isinstance(ex.get(k), str) and ex.get(k)
        adv = ex.get("action_advice")
        assert isinstance(adv, list) and len(adv) >= 3
        hrc = ex.get("highlighted_risk_clauses")
        assert isinstance(hrc, list)
        risks_n = len(sa.get("risks") or [])
        assert len(hrc) == min(risks_n, 20)
        assert label


def validate_contract_localization_samples() -> None:
    """
    Part 5：定位样例专项校验 —— risks 与 highlighted_risk_clauses 对齐，且正则类风险带 matched_text。
    """
    loc_specs = (
        ("sample_loc_hidden_fee", SAMPLE_LOC_HIDDEN_FEE, {"monthly_rent": 900.0, "deposit_amount": None}),
        ("sample_loc_landlord_access", SAMPLE_LOC_LANDLORD_ACCESS, {"monthly_rent": 950.0, "deposit_amount": None}),
        ("sample_loc_tenant_repairs", SAMPLE_LOC_TENANT_REPAIRS, {"monthly_rent": 880.0, "deposit_amount": None}),
    )
    for label, text, kwargs in loc_specs:
        out = analyze_contract_with_explain(contract_text=text, **kwargs)
        sa = out["structured_analysis"]
        ex = out["explain"]
        risks = sa.get("risks")
        assert isinstance(risks, list), label
        assert len(risks) >= 1, label
        hrc = ex.get("highlighted_risk_clauses")
        assert isinstance(hrc, list), label
        assert len(hrc) == min(len(risks), 20), label
        for r in risks:
            assert isinstance(r, dict), label
            assert "matched_text" in r and isinstance(r.get("matched_text"), str), label
            rid = str(r.get("rule_id") or "")
            if rid != "deposit_amount_high":
                assert str(r.get("matched_text") or "").strip(), f"{label}: {rid} empty matched_text"
        for card in hrc:
            assert isinstance(card, dict), label
            assert "matched_text" in card and isinstance(card.get("matched_text"), str), label


def validate_contract_analysis_empty_risk_fallback() -> None:
    """无规则命中时 risks / highlighted_risk_clauses 均为空 list。"""
    out = analyze_contract_with_explain(
        contract_text="This line contains only generic words like hello and world.",
        monthly_rent=None,
        deposit_amount=None,
    )
    sa = out["structured_analysis"]
    ex = out["explain"]
    assert isinstance(sa.get("risks"), list)
    assert sa["risks"] == []
    assert isinstance(ex.get("highlighted_risk_clauses"), list)
    assert ex["highlighted_risk_clauses"] == []


def test_contract_analysis_samples() -> None:
    """与项目 ``test_*.py`` 风格兼容：可直接被 pytest 收集。"""
    validate_contract_analysis_samples()
    validate_contract_localization_samples()
    validate_contract_analysis_empty_risk_fallback()


def run_contract_analysis_demo() -> None:
    """
    依次分析全部样例合同，在 stdout 输出 explain 四层字段（分段标题）。
    """
    print("===== RentalAI Phase 3 · 样例合同分析演示 =====\n")
    for label, text, kwargs in _sample_specs():
        out = analyze_contract_with_explain(contract_text=text, **kwargs)
        ex = out.get("explain") or {}
        print(f"── 样例：{label} ──")
        print()
        print("【overall_conclusion】")
        print(ex.get("overall_conclusion", "—"))
        print()
        print("【key_risk_summary】")
        print(ex.get("key_risk_summary", "—"))
        print()
        print("【missing_clause_summary】")
        print(ex.get("missing_clause_summary", "—"))
        print()
        print("【action_advice】")
        for i, line in enumerate(ex.get("action_advice") or [], start=1):
            print(f"  {i}. {line}")
        print()
        print("─" * 56)
        print()


if __name__ == "__main__":
    run_contract_analysis_demo()
