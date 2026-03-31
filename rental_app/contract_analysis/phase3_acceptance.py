"""
Phase 3 收尾：合同分析模块总验收（demo / test 统一入口）。

在 ``rental_app`` 目录下::

    python -m contract_analysis.phase3_acceptance

或在代码中::

    from contract_analysis.phase3_acceptance import run_phase3_acceptance, test_phase3_acceptance

    run_phase3_acceptance()
    test_phase3_acceptance()  # 供 pytest 收集
"""

from __future__ import annotations

import sys
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from .sample_contracts_data import (
    SAMPLE_COMPLETENESS_MISSING_NOTICE_REPAIR,
    SAMPLE_COMPLETENESS_SHORT_INCOMPLETE,
    SAMPLE_CONTRACT_HIDDEN_FEES_PENALTY,
    SAMPLE_CONTRACT_HIGH_RISK,
    SAMPLE_CONTRACT_MEDIUM_RISK,
    SAMPLE_CONTRACT_SAFE,
    SAMPLE_CONTRACT_UNFAIR_ENTRY,
    SAMPLE_LOC_LANDLORD_ACCESS,
    SAMPLE_LOC_TENANT_REPAIRS,
)
from .service import analyze_contract_file_with_explain, analyze_contract_with_explain

# 与 ``contract_analyzer._normalize_analysis_output`` / ``contract_explainer._normalize_explain_out`` 对齐
PHASE3_STRUCTURED_REQUIRED_KEYS: tuple[str, ...] = (
    "summary",
    "risks",
    "missing_items",
    "recommendations",
    "detected_topics",
    "clause_list",
    "clause_risk_map",
    "clause_severity_summary",
    "contract_completeness",
    "risk_category_summary",
    "risk_category_groups",
    "meta",
)

PHASE3_EXPLAIN_REQUIRED_KEYS: tuple[str, ...] = (
    "overall_conclusion",
    "key_risk_summary",
    "missing_clause_summary",
    "action_advice",
    "risk_category_summary",
    "risk_category_groups",
    "highlighted_risk_clauses",
    "clause_overview",
    "clause_risk_overview",
    "clause_severity_overview",
    "contract_completeness_overview",
)

# (场景 id, 说明, 合同文本, analyze_contract_with_explain 参数)
PHASE3_TEXT_SCENARIOS: list[tuple[str, str, str, dict[str, Any]]] = [
    (
        "safe_low_risk",
        "安全 / 低风险合同",
        SAMPLE_CONTRACT_SAFE,
        {"monthly_rent": 950.0, "deposit_amount": 1095.0},
    ),
    (
        "medium_risk",
        "中等风险合同",
        SAMPLE_CONTRACT_MEDIUM_RISK,
        {"monthly_rent": 850.0, "deposit_amount": 850.0},
    ),
    (
        "high_risk",
        "高风险合同",
        SAMPLE_CONTRACT_HIGH_RISK,
        {"monthly_rent": 800.0, "deposit_amount": 2500.0},
    ),
    (
        "hidden_fees",
        "隐藏费用 / 罚金表述",
        SAMPLE_CONTRACT_HIDDEN_FEES_PENALTY,
        {"monthly_rent": 850.0, "deposit_amount": 850.0},
    ),
    (
        "landlord_access_no_notice",
        "房东进入权 / 未合理通知（不公平进入）",
        SAMPLE_CONTRACT_UNFAIR_ENTRY,
        {"monthly_rent": 950.0, "deposit_amount": 950.0},
    ),
    (
        "landlord_access_loc",
        "房东随时进入（定位短样例）",
        SAMPLE_LOC_LANDLORD_ACCESS,
        {"monthly_rent": 950.0, "deposit_amount": None},
    ),
    (
        "tenant_all_repairs",
        "租客承担全部维修",
        SAMPLE_LOC_TENANT_REPAIRS,
        {"monthly_rent": 880.0, "deposit_amount": None},
    ),
    (
        "missing_notice_repair_completeness",
        "缺通知期 / 缺维修（完整性专项）",
        SAMPLE_COMPLETENESS_MISSING_NOTICE_REPAIR,
        {"monthly_rent": 1200.0, "deposit_amount": 1200.0},
    ),
    (
        "short_incomplete",
        "极短不完整合同（完整性低分）",
        SAMPLE_COMPLETENESS_SHORT_INCOMPLETE,
        {"monthly_rent": 500.0, "deposit_amount": 500.0},
    ),
]


def assert_phase3_pipeline_result(out: dict[str, Any], *, label: str = "") -> None:
    """断言 ``analyze_contract_with_explain`` / ``analyze_contract_file_with_explain`` 返回形状。"""
    prefix = f"{label}: " if label else ""
    assert isinstance(out, dict), f"{prefix}result is not dict"
    assert "structured_analysis" in out and "explain" in out, f"{prefix}missing layers"
    sa = out["structured_analysis"]
    ex = out["explain"]
    assert isinstance(sa, dict), f"{prefix}structured_analysis"
    assert isinstance(ex, dict), f"{prefix}explain"

    for k in PHASE3_STRUCTURED_REQUIRED_KEYS:
        assert k in sa, f"{prefix}structured_analysis missing {k}"
        assert sa[k] is not None, f"{prefix}structured_analysis[{k}] is None"
    for k in (
        "risks",
        "missing_items",
        "recommendations",
        "detected_topics",
        "clause_list",
        "clause_risk_map",
        "clause_severity_summary",
        "risk_category_summary",
        "risk_category_groups",
    ):
        assert isinstance(sa[k], list), f"{prefix}structured_analysis[{k}] not list"

    cc = sa["contract_completeness"]
    assert isinstance(cc, dict), f"{prefix}contract_completeness"
    for ck in ("missing_core_items", "unclear_items", "checked_items"):
        assert ck in cc, f"{prefix}contract_completeness.{ck}"
        if ck != "checked_items":
            assert isinstance(cc[ck], list), f"{prefix}contract_completeness.{ck}"

    assert isinstance(sa["meta"], dict), f"{prefix}meta"

    for k in PHASE3_EXPLAIN_REQUIRED_KEYS:
        assert k in ex, f"{prefix}explain missing {k}"
        assert ex[k] is not None, f"{prefix}explain[{k}] is None"
    for k in (
        "highlighted_risk_clauses",
        "risk_category_summary",
        "risk_category_groups",
        "clause_overview",
        "clause_risk_overview",
        "clause_severity_overview",
        "action_advice",
    ):
        assert isinstance(ex[k], list), f"{prefix}explain[{k}] not list"

    cco = ex["contract_completeness_overview"]
    assert isinstance(cco, dict), f"{prefix}contract_completeness_overview"
    for ck in ("missing_core_items", "unclear_items"):
        assert isinstance(cco[ck], list), f"{prefix}contract_completeness_overview.{ck}"

    pres = out.get("presentation")
    if pres is not None:
        assert isinstance(pres, dict), f"{prefix}presentation"
        assert "sections" in pres and "plain_text" in pres, f"{prefix}presentation shape"


def assert_phase3_empty_and_no_hit_safe() -> None:
    """无正文 / 无规则命中时仍为稳定结构、空 list 安全。"""
    empty = analyze_contract_with_explain(contract_text="   \n  ")
    assert_phase3_pipeline_result(empty, label="empty_text")
    esa = empty["structured_analysis"]
    assert esa["risks"] == []
    assert esa["clause_list"] == []

    no_hit = analyze_contract_with_explain(
        contract_text="Hello world generic text only.",
        monthly_rent=None,
        deposit_amount=None,
    )
    assert_phase3_pipeline_result(no_hit, label="no_rule_hit")
    assert isinstance(no_hit["structured_analysis"]["risks"], list)
    assert isinstance(no_hit["explain"]["highlighted_risk_clauses"], list)


def run_phase3_acceptance(*, include_file_formats: bool = True, verbose: bool = True) -> None:
    """
    最小总验收：文本场景 +（可选）固定 sample_contract.* 的 txt/pdf/docx。

    ``include_file_formats=False`` 时仅跑内存文本，便于无二进制样例的环境。
    """
    if verbose:
        print("=== Phase 3 合同分析 · 总验收 ===\n")

    n = 0
    for sid, desc, text, kwargs in PHASE3_TEXT_SCENARIOS:
        out = analyze_contract_with_explain(contract_text=text, **kwargs)
        assert_phase3_pipeline_result(out, label=sid)
        n += 1
        if verbose:
            sa = out["structured_analysis"]
            print(f"[OK] text:{sid} — {desc}")
            print(
                f"     risks={len(sa['risks'])} clauses={len(sa['clause_list'])} "
                f"cc_score={sa['contract_completeness'].get('completeness_score')}"
            )

    assert_phase3_empty_and_no_hit_safe()
    n += 2
    if verbose:
        print("[OK] edge: empty_contract_text + no_rule_hit")

    if include_file_formats:
        from .demo_contract_document_readers import sample_contract_paths

        txt_p, pdf_p, docx_p = sample_contract_paths()
        for path, kind in ((txt_p, "txt"), (pdf_p, "pdf"), (docx_p, "docx")):
            if not path.is_file():
                if verbose:
                    print(f"[SKIP] file:{kind} — not found: {path.name}")
                continue
            out = analyze_contract_file_with_explain(file_path=path)
            assert_phase3_pipeline_result(out, label=f"file_{kind}")
            n += 1
            if verbose:
                sa = out["structured_analysis"]
                meta = sa.get("meta") or {}
                print(f"[OK] file:{kind} — {path.name} source_type={meta.get('source_type')}")

    if verbose:
        print(f"\n=== 总验收通过 · {n} 步断言场景 ===")


def test_phase3_acceptance() -> None:
    """pytest：总验收（含文件格式，缺 pdf/docx 时跳过该格式）。"""
    run_phase3_acceptance(include_file_formats=True, verbose=False)


if __name__ == "__main__":
    run_phase3_acceptance()
