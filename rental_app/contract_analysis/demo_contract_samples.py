"""
Phase 3 合同分析：样例合同演示与最小校验入口。

运行::

    python -m contract_analysis.demo_contract_samples

或在代码中调用 ``run_contract_analysis_demo()``。
"""

from __future__ import annotations

from typing import Any

from .sample_contracts_data import (
    SAMPLE_CAT_ACCESS_NOTICE,
    SAMPLE_CAT_DEPOSIT_ISSUE,
    SAMPLE_CAT_HIDDEN_FEE,
    SAMPLE_CAT_RENT_TERMINATION,
    SAMPLE_CLAUSE_DEPOSIT_RENT,
    SAMPLE_CLAUSE_NOTICE_TERMINATION,
    SAMPLE_CLAUSE_PETS_SUBLETTING,
    SAMPLE_CLAUSE_REPAIRS_BILLS,
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
        # Part 6：分类 / 分组专项（各样例触发不同 risk_category）
        (
            "sample_cat_deposit_issue",
            SAMPLE_CAT_DEPOSIT_ISSUE,
            {"monthly_rent": 950.0, "deposit_amount": 950.0},
        ),
        (
            "sample_cat_hidden_fee",
            SAMPLE_CAT_HIDDEN_FEE,
            {"monthly_rent": 950.0, "deposit_amount": 950.0},
        ),
        (
            "sample_cat_access_notice",
            SAMPLE_CAT_ACCESS_NOTICE,
            {"monthly_rent": 950.0, "deposit_amount": 950.0},
        ),
        (
            "sample_cat_rent_termination",
            SAMPLE_CAT_RENT_TERMINATION,
            {"monthly_rent": 950.0, "deposit_amount": 950.0},
        ),
        # Part 7：条款切分 + clause_type 多场景（编号条款、多类型）
        (
            "sample_clause_deposit_rent",
            SAMPLE_CLAUSE_DEPOSIT_RENT,
            {"monthly_rent": 950.0, "deposit_amount": 950.0},
        ),
        (
            "sample_clause_notice_termination",
            SAMPLE_CLAUSE_NOTICE_TERMINATION,
            {"monthly_rent": 950.0, "deposit_amount": 950.0},
        ),
        (
            "sample_clause_repairs_bills",
            SAMPLE_CLAUSE_REPAIRS_BILLS,
            {"monthly_rent": 950.0, "deposit_amount": 950.0},
        ),
        (
            "sample_clause_pets_subletting",
            SAMPLE_CLAUSE_PETS_SUBLETTING,
            {"monthly_rent": 950.0, "deposit_amount": 950.0},
        ),
    ]


# Part 6：各专项样例应至少出现这些 risk_category（非 general 为主）
_CATEGORY_SAMPLES_EXPECT: dict[str, set[str]] = {
    "sample_cat_deposit_issue": {"deposit"},
    "sample_cat_hidden_fee": {"fees"},
    "sample_cat_access_notice": {"access"},
    "sample_cat_rent_termination": {"rent_increase", "termination"},
}

# Part 7：同上样例在 clause_list 中应覆盖的 clause_type（与风险层 fees 等可不完全同名）
_CATEGORY_SAMPLES_CLAUSE_EXPECT: dict[str, set[str]] = {
    "sample_cat_deposit_issue": {"deposit"},
    "sample_cat_hidden_fee": {"bills"},
    "sample_cat_access_notice": {"access"},
    "sample_cat_rent_termination": {"rent_increase", "termination"},
}

# Part 7：clause_type 专项（存款+月租、通知+终止、维修+账单、宠物+转租）
_CLAUSE_TYPE_SAMPLES_EXPECT: dict[str, set[str]] = {
    "sample_clause_deposit_rent": {"deposit", "rent"},
    "sample_clause_notice_termination": {"notice", "termination"},
    "sample_clause_repairs_bills": {"repairs", "bills", "inventory"},
    "sample_clause_pets_subletting": {"pets", "subletting"},
}


def _clause_type_specs() -> list[tuple[str, str, dict[str, Any]]]:
    """Part 7 条款类型专项样例。"""
    return [
        (k, v, w)
        for (k, v, w) in _sample_specs()
        if k in _CLAUSE_TYPE_SAMPLES_EXPECT
    ]


def _category_specs() -> list[tuple[str, str, dict[str, Any]]]:
    """仅 Part 6 分类专项样例。"""
    return [
        (k, v, w)
        for (k, v, w) in _sample_specs()
        if k in _CATEGORY_SAMPLES_EXPECT
    ]


def validate_contract_category_samples() -> None:
    """断言分类专项样例命中预期 category，且各层 list 字段稳定。"""
    for label, text, kwargs in _category_specs():
        out = analyze_contract_with_explain(contract_text=text, **kwargs)
        sa = out["structured_analysis"]
        ex = out["explain"]
        assert isinstance(sa.get("risks"), list), label
        assert isinstance(sa.get("clause_list"), list), label
        assert isinstance(sa.get("risk_category_summary"), list), label
        assert isinstance(sa.get("risk_category_groups"), list), label
        assert isinstance(ex.get("risk_category_summary"), list), label
        assert isinstance(ex.get("risk_category_groups"), list), label
        assert isinstance(ex.get("clause_overview"), list), label
        assert isinstance(ex.get("highlighted_risk_clauses"), list), label
        assert len(sa["risk_category_groups"]) == len(sa["risk_category_summary"]), label
        assert len(ex["risk_category_groups"]) == len(ex["risk_category_summary"]), label
        risks = sa.get("risks") or []
        assert len(risks) >= 1, label
        risk_cats = {str(r.get("risk_category") or "").strip() for r in risks if isinstance(r, dict)}
        risk_cats.discard("")
        summ_cats = {
            str(row.get("category") or "").strip()
            for row in (sa.get("risk_category_summary") or [])
            if isinstance(row, dict)
        }
        summ_cats.discard("")
        assert risk_cats == summ_cats, f"{label}: risks vs summary categories {risk_cats!r} vs {summ_cats!r}"
        expected = _CATEGORY_SAMPLES_EXPECT[label]
        assert expected <= risk_cats, f"{label}: expected {expected!r} got {risk_cats!r}"
        cexp = _CATEGORY_SAMPLES_CLAUSE_EXPECT.get(label)
        if cexp:
            clause_types = {
                str(c.get("clause_type") or "").strip()
                for c in (sa.get("clause_list") or [])
                if isinstance(c, dict)
            }
            clause_types.discard("")
            assert cexp <= clause_types, f"{label}: clause_type set {clause_types!r} vs {cexp!r}"
        for r in risks:
            assert isinstance(r, dict), label
            assert str(r.get("risk_category") or "").strip(), label
        for row in sa.get("risk_category_summary") or []:
            if isinstance(row, dict):
                assert isinstance(row.get("count"), int), label


def validate_contract_clause_type_samples() -> None:
    """Part 7：专项样例命中预期 clause_type，且 clause_list / clause_overview 字段稳定。"""
    for label, text, kwargs in _clause_type_specs():
        out = analyze_contract_with_explain(contract_text=text, **kwargs)
        sa = out["structured_analysis"]
        ex = out["explain"]
        assert isinstance(sa.get("clause_list"), list), label
        assert isinstance(ex.get("clause_overview"), list), label
        clauses = sa.get("clause_list") or []
        overview = ex.get("clause_overview") or []
        assert len(clauses) >= 2, label
        assert len(overview) == len(clauses), f"{label}: overview vs clauses {len(overview)} vs {len(clauses)}"
        expected = _CLAUSE_TYPE_SAMPLES_EXPECT[label]
        clause_types: set[str] = set()
        for c in clauses:
            assert isinstance(c, dict), label
            assert str(c.get("clause_id") or "").strip(), label
            ct = str(c.get("clause_type") or "").strip()
            assert ct, label
            assert isinstance(c.get("matched_keywords"), list), label
            clause_types.add(ct)
        for row in overview:
            assert isinstance(row, dict), label
            assert str(row.get("clause_id") or "").strip(), label
            assert str(row.get("clause_type") or "").strip(), label
            assert isinstance(row.get("matched_keywords"), list), label
        assert expected <= clause_types, f"{label}: clause_type set {clause_types!r} vs {expected!r}"


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
        assert isinstance(sa.get("clause_list"), list), label
        assert len(sa.get("clause_list") or []) >= 1, label
        assert isinstance(sa.get("risk_category_groups"), list)
        assert isinstance(sa.get("risk_category_summary"), list)
        assert len(sa["risk_category_groups"]) == len(sa["risk_category_summary"])
        meta = sa.get("meta")
        assert isinstance(meta, dict)
        assert meta.get("source_type") == "text"
        for k in ("overall_conclusion", "key_risk_summary", "missing_clause_summary"):
            assert isinstance(ex.get(k), str) and ex.get(k)
        adv = ex.get("action_advice")
        assert isinstance(adv, list) and len(adv) >= 3
        hrc = ex.get("highlighted_risk_clauses")
        assert isinstance(hrc, list)
        assert isinstance(ex.get("risk_category_groups"), list)
        assert isinstance(ex.get("risk_category_summary"), list)
        assert isinstance(ex.get("clause_overview"), list), label
        assert len(ex["risk_category_groups"]) == len(ex["risk_category_summary"])
        pres = out.get("presentation") or {}
        sec_ids = [s.get("id") for s in (pres.get("sections") or []) if isinstance(s, dict)]
        assert "clause_overview" in sec_ids, label
        assert "risk_category_summary" in sec_ids, label
        assert "risk_category_groups" in sec_ids, label
        for s in pres.get("sections") or []:
            if not isinstance(s, dict) or s.get("id") != "risk_category_groups":
                continue
            for it in s.get("items") or []:
                if isinstance(it, dict):
                    assert "risk_titles" in it, label
        risks_n = len(sa.get("risks") or [])
        assert len(hrc) == min(risks_n, 20)
        for r in sa.get("risks") or []:
            assert isinstance(r, dict), label
            assert str(r.get("risk_category") or "").strip(), label
            assert str(r.get("risk_code") or "").strip(), label
        for card in hrc:
            assert str(card.get("risk_category") or "").strip(), label
            assert str(card.get("risk_code") or "").strip(), label
        for c in sa.get("clause_list") or []:
            assert isinstance(c, dict), label
            assert str(c.get("clause_id") or "").strip(), label
            assert isinstance(c.get("clause_type"), str) and str(c.get("clause_type") or "").strip(), label
            assert isinstance(c.get("matched_keywords"), list), label
        cov = ex.get("clause_overview") or []
        assert isinstance(cov, list), label
        assert len(cov) == len(sa.get("clause_list") or []), label
        for row in cov:
            assert isinstance(row, dict), label
            assert str(row.get("clause_id") or "").strip(), label
            assert isinstance(row.get("clause_type"), str) and str(row.get("clause_type") or "").strip(), label
            assert isinstance(row.get("matched_keywords"), list), label
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
        assert isinstance(sa.get("clause_list"), list), label
        assert len(sa.get("clause_list") or []) >= 1, label
        assert isinstance(sa.get("risk_category_groups"), list), label
        assert isinstance(sa.get("risk_category_summary"), list), label
        assert isinstance(ex.get("risk_category_groups"), list), label
        assert isinstance(ex.get("risk_category_summary"), list), label
        assert isinstance(ex.get("clause_overview"), list), label
        assert len(sa["risk_category_groups"]) == len(sa["risk_category_summary"]), label
        hrc = ex.get("highlighted_risk_clauses")
        assert isinstance(hrc, list), label
        assert len(hrc) == min(len(risks), 20), label
        for r in risks:
            assert isinstance(r, dict), label
            assert "matched_text" in r and isinstance(r.get("matched_text"), str), label
            assert str(r.get("risk_category") or "").strip(), label
            assert str(r.get("risk_code") or "").strip(), label
            rid = str(r.get("rule_id") or "")
            if rid != "deposit_amount_high":
                assert str(r.get("matched_text") or "").strip(), f"{label}: {rid} empty matched_text"
        for card in hrc:
            assert isinstance(card, dict), label
            assert "matched_text" in card and isinstance(card.get("matched_text"), str), label
            assert str(card.get("risk_category") or "").strip(), label
            assert str(card.get("risk_code") or "").strip(), label


def validate_contract_empty_contract_text_clause_list() -> None:
    """无正文时 ``clause_list`` 为空 list（与 ``risks`` 空分支一致）。"""
    out = analyze_contract_with_explain(contract_text="   \n  ")
    sa = out["structured_analysis"]
    ex = out["explain"]
    assert isinstance(sa.get("clause_list"), list)
    assert sa.get("clause_list") == []
    assert isinstance(ex.get("clause_overview"), list)
    assert ex.get("clause_overview") == []


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
    assert isinstance(sa.get("clause_list"), list)
    assert len(sa["clause_list"]) >= 1
    assert isinstance(sa.get("risk_category_groups"), list)
    assert isinstance(sa.get("risk_category_summary"), list)
    assert sa.get("risk_category_groups") == []
    assert sa.get("risk_category_summary") == []
    assert isinstance(ex.get("highlighted_risk_clauses"), list)
    assert ex["highlighted_risk_clauses"] == []
    assert isinstance(ex.get("risk_category_groups"), list)
    assert isinstance(ex.get("risk_category_summary"), list)
    assert ex.get("risk_category_groups") == []
    assert ex.get("risk_category_summary") == []
    assert isinstance(ex.get("clause_overview"), list)
    assert len(ex["clause_overview"]) >= 1


def test_contract_analysis_samples() -> None:
    """与项目 ``test_*.py`` 风格兼容：可直接被 pytest 收集。"""
    validate_contract_analysis_samples()
    validate_contract_localization_samples()
    validate_contract_category_samples()
    validate_contract_clause_type_samples()
    validate_contract_empty_contract_text_clause_list()
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
        print("【clause_overview】")
        for row in ex.get("clause_overview") or []:
            if isinstance(row, dict):
                print(
                    f"  - {row.get('clause_id')} [{row.get('clause_type')}] "
                    f"{row.get('short_clause_preview')} | keywords={row.get('matched_keywords')}"
                )
        if not (ex.get("clause_overview") or []):
            print("  (none)")
        print()
        print("【risk_category_summary】")
        for row in ex.get("risk_category_summary") or []:
            if isinstance(row, dict):
                print(
                    f"  - {row.get('category')}: count={row.get('count')} "
                    f"severity={row.get('highest_severity')} | {row.get('short_summary')}"
                )
        if not (ex.get("risk_category_summary") or []):
            print("  (none)")
        print()
        print("【risk_category_groups】")
        for g in ex.get("risk_category_groups") or []:
            if not isinstance(g, dict):
                continue
            c = g.get("category")
            titles = [
                str(r.get("title") or r.get("rule_id") or "").strip()
                for r in (g.get("risks") or [])
                if isinstance(r, dict)
            ]
            titles = [t for t in titles if t]
            print(f"  · {c}: {', '.join(titles) if titles else '—'}")
        if not (ex.get("risk_category_groups") or []):
            print("  (none)")
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
