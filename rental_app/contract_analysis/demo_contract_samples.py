"""
Phase 3 合同分析：样例合同演示与最小校验入口。

运行::

    python -m contract_analysis.demo_contract_samples

或在代码中调用 ``run_contract_analysis_demo()``。

Part 10 第 4 步：``sample_completeness_*.txt`` 四样例用于完整性检查收尾；期望见 ``_COMPLETENESS_FINALE_EXPECT``。
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
    SAMPLE_CLAUSE_RISK_ACCESS_NOTICE,
    SAMPLE_CLAUSE_RISK_DEPOSIT_HIGH,
    SAMPLE_CLAUSE_RISK_HIDDEN_FEE,
    SAMPLE_CLAUSE_RISK_TENANT_REPAIRS,
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
    SAMPLE_SEVERITY_LOW_INCOMPLETE_CLAUSE,
    SAMPLE_SEVERITY_MEDIUM_FEE_CLAUSE,
    SAMPLE_SEVERITY_MIXED_CLAUSES,
    SAMPLE_SEVERITY_ONE_CLAUSE_MULTI_HIGH,
    SAMPLE_COMPLETENESS_VERY_COMPLETE,
    SAMPLE_COMPLETENESS_MISSING_NOTICE_REPAIR,
    SAMPLE_COMPLETENESS_MISSING_DEPOSIT_ACCESS,
    SAMPLE_COMPLETENESS_SHORT_INCOMPLETE,
)
from .contract_models import coerce_contract_completeness_overall_status
from .service import analyze_contract_with_explain


def _assert_clause_risk_map_shape(sa: dict[str, Any], label: str) -> None:
    """Part 8：``clause_risk_map`` 为 list，项字段齐全且 ``clause_id`` 属于 ``clause_list``。"""
    crm = sa.get("clause_risk_map")
    assert isinstance(crm, list), label
    clause_ids = {
        str(c.get("clause_id") or "").strip()
        for c in (sa.get("clause_list") or [])
        if isinstance(c, dict)
    }
    risks_n = len(sa.get("risks") or [])
    assert len(crm) <= risks_n, label
    for row in crm:
        assert isinstance(row, dict), label
        assert str(row.get("clause_id") or "").strip(), label
        assert str(row.get("risk_title") or "").strip(), label
        assert str(row.get("risk_category") or "").strip(), label
        assert str(row.get("severity") or "").strip(), label
        assert isinstance(row.get("matched_keyword"), str), label
        assert isinstance(row.get("matched_text"), str), label
        assert isinstance(row.get("location_hint"), str), label
        assert str(row.get("link_reason") or "").strip(), label
        cid = str(row.get("clause_id") or "").strip()
        assert cid in clause_ids, f"{label}: clause_risk_map references unknown clause_id {cid!r}"


def _assert_clause_severity_summary_shape(sa: dict[str, Any], label: str) -> None:
    """Part 9：``clause_severity_summary`` 为 list，项字段类型稳定；与 ``clause_risk_map`` 计数/分值一致。"""
    css = sa.get("clause_severity_summary")
    assert isinstance(css, list), label
    crm = sa.get("clause_risk_map")
    crm_list = crm if isinstance(crm, list) else []
    _w = {"high": 3, "medium": 2, "low": 1}

    def _row_weight(row: dict[str, Any]) -> int:
        s = str(row.get("severity") or "medium").strip().lower()
        if s not in ("high", "medium", "low"):
            s = "medium"
        return _w[s]

    for item in css:
        assert isinstance(item, dict), label
        assert str(item.get("clause_id") or "").strip(), label
        assert isinstance(item.get("clause_type"), str), label
        assert isinstance(item.get("severity_score"), int), label
        assert isinstance(item.get("highest_severity"), str), label
        assert str(item.get("highest_severity") or "").strip() in ("high", "medium", "low"), label
        assert isinstance(item.get("linked_risk_count"), int), label
        assert isinstance(item.get("linked_risk_titles"), list), label
        assert isinstance(item.get("short_clause_preview"), str), label
        assert isinstance(item.get("location_hint"), str), label
        cid = str(item.get("clause_id") or "").strip()
        links_for = [
            r
            for r in crm_list
            if isinstance(r, dict) and str(r.get("clause_id") or "").strip() == cid
        ]
        assert int(item.get("linked_risk_count") or 0) == len(links_for), label
        assert int(item.get("severity_score") or 0) == sum(_row_weight(x) for x in links_for), label


def _assert_contract_completeness_shape(sa: dict[str, Any], label: str) -> None:
    """Part 10：``contract_completeness`` 稳定存在且字段类型齐全。"""
    cc = sa.get("contract_completeness")
    assert isinstance(cc, dict), label
    assert isinstance(cc.get("overall_status"), str), label
    os = str(cc.get("overall_status") or "").strip()
    assert os in ("unknown", "complete", "partially_complete", "incomplete", "ok", "mixed"), label
    assert isinstance(cc.get("completeness_score"), int), label
    assert 0 <= int(cc.get("completeness_score") or 0) <= 100, label
    assert isinstance(cc.get("checked_items"), list), label
    assert isinstance(cc.get("missing_core_items"), list), label
    assert isinstance(cc.get("unclear_items"), list), label
    assert isinstance(cc.get("summary"), str), label
    assert len(cc.get("checked_items") or []) == 10, label


# Part 10 第 4 步：收尾样例期望（completeness_score 与 overall_status 与规则引擎对齐；短文本允许 ± 分漂移）
_COMPLETENESS_FINALE_EXPECT: dict[str, tuple[int, int, str]] = {
    "sample_completeness_very_complete": (100, 100, "complete"),
    "sample_completeness_missing_notice_repair": (70, 70, "partially_complete"),
    "sample_completeness_missing_deposit_access": (80, 80, "partially_complete"),
    "sample_completeness_short_incomplete": (10, 20, "incomplete"),
}


def _assert_completeness_finale_expectations(sa: dict[str, Any], ex: dict[str, Any], label: str) -> None:
    """Part 10 收尾：结构化层与 explain overview 分数/状态一致，列表字段稳定。"""
    if label not in _COMPLETENESS_FINALE_EXPECT:
        return
    lo, hi, st = _COMPLETENESS_FINALE_EXPECT[label]
    cc = sa.get("contract_completeness")
    assert isinstance(cc, dict), label
    cs = int(cc.get("completeness_score", 0))
    assert lo <= cs <= hi, f"{label}: completeness_score {cs} not in [{lo},{hi}]"
    assert str(cc.get("overall_status") or "").strip() == st, f"{label}: overall_status {cc.get('overall_status')} != {st}"
    cco = ex.get("contract_completeness_overview")
    assert isinstance(cco, dict), label
    ccs = int(cco.get("completeness_score", 0))
    assert lo <= ccs <= hi, f"{label}: contract_completeness_overview.completeness_score {ccs} not in [{lo},{hi}]"
    assert str(cco.get("overall_status") or "").strip() == st, f"{label}: overview overall_status {cco.get('overall_status')} != {st}"
    assert isinstance(cc.get("missing_core_items"), list), label
    assert isinstance(cc.get("unclear_items"), list), label
    assert isinstance(cco.get("missing_core_items"), list), label
    assert isinstance(cco.get("unclear_items"), list), label


def _assert_contract_completeness_overview_explain(ex: dict[str, Any], sa: dict[str, Any], label: str) -> None:
    """Part 10 Step 3：explain.contract_completeness_overview 稳定键，与结构化层一致。"""
    cco = ex.get("contract_completeness_overview")
    assert isinstance(cco, dict), label
    os = str(cco.get("overall_status") or "").strip()
    assert os in ("unknown", "complete", "partially_complete", "incomplete"), label
    assert isinstance(cco.get("completeness_score"), int), label
    assert 0 <= int(cco.get("completeness_score") or 0) <= 100, label
    assert isinstance(cco.get("missing_core_items"), list), label
    assert isinstance(cco.get("unclear_items"), list), label
    assert isinstance(cco.get("short_summary"), str), label
    cc = sa.get("contract_completeness")
    if isinstance(cc, dict):
        assert os == coerce_contract_completeness_overall_status(cc.get("overall_status")), label
        assert int(cco.get("completeness_score") or 0) == int(cc.get("completeness_score") or 0), label


def _assert_clause_severity_score_descending(sa: dict[str, Any], label: str) -> None:
    """``clause_severity_summary`` 按 ``severity_score`` 降序（与 ``build_clause_severity_summary`` 一致）。"""
    css = sa.get("clause_severity_summary")
    assert isinstance(css, list), label
    scores: list[int] = []
    for x in css:
        if isinstance(x, dict):
            try:
                scores.append(int(x.get("severity_score", 0)))
            except (TypeError, ValueError):
                scores.append(0)
    assert scores == sorted(scores, reverse=True), f"{label}: severity_score 非降序 {scores!r}"


def _assert_clause_severity_explain_aligned(sa: dict[str, Any], ex: dict[str, Any], label: str) -> None:
    """explain.clause_severity_overview 与 structured clause_severity_summary 条数、clause_id 顺序一致。"""
    css = sa.get("clause_severity_summary")
    cso = ex.get("clause_severity_overview")
    assert isinstance(css, list), label
    assert isinstance(cso, list), label
    assert len(css) == len(cso), f"{label}: len summary {len(css)} vs overview {len(cso)}"
    for a, b in zip(css, cso):
        if not isinstance(a, dict) or not isinstance(b, dict):
            continue
        assert str(a.get("clause_id") or "").strip() == str(b.get("clause_id") or "").strip(), label
        assert int(a.get("severity_score") or 0) == int(b.get("severity_score") or 0), label


def _assert_clause_severity_overview_explain(ex: dict[str, Any], label: str) -> None:
    """Explain：``clause_severity_overview`` 为稳定 list；项字段与 Top risky clauses 卡片对齐。"""
    cso = ex.get("clause_severity_overview")
    assert isinstance(cso, list), label
    for row in cso:
        assert isinstance(row, dict), label
        assert str(row.get("clause_id") or "").strip(), label
        assert isinstance(row.get("clause_type"), str) and str(row.get("clause_type") or "").strip(), label
        assert isinstance(row.get("severity_score"), int), label
        assert str(row.get("highest_severity") or "").strip() in ("high", "medium", "low"), label
        assert isinstance(row.get("linked_risk_count"), int), label
        assert str(row.get("short_clause_preview") or "").strip(), label
        assert isinstance(row.get("linked_risk_titles"), list), label


def _assert_clause_risk_overview_explain(ex: dict[str, Any], label: str) -> None:
    """Explain：``clause_risk_overview`` 为 list；非空时每块含 ``linked_risks`` 子项。"""
    cro = ex.get("clause_risk_overview")
    assert isinstance(cro, list), label
    for block in cro:
        assert isinstance(block, dict), label
        assert str(block.get("clause_id") or "").strip(), label
        assert isinstance(block.get("clause_type"), str) and str(block.get("clause_type") or "").strip(), label
        assert str(block.get("short_clause_preview") or "").strip(), label
        lr = block.get("linked_risks")
        assert isinstance(lr, list), label
        assert len(lr) >= 1, label
        for x in lr:
            assert isinstance(x, dict), label
            assert str(x.get("risk_title") or "").strip(), label
            assert str(x.get("risk_category") or "").strip(), label
            assert str(x.get("severity") or "").strip(), label
            assert isinstance(x.get("matched_keyword"), str), label
            assert str(x.get("short_reason") or "").strip(), label


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
        # Part 8：条款—风险联动专项（clause_risk_map / clause_risk_overview）
        (
            "sample_clause_risk_deposit_high",
            SAMPLE_CLAUSE_RISK_DEPOSIT_HIGH,
            {"monthly_rent": 1000.0, "deposit_amount": 6000.0},
        ),
        (
            "sample_clause_risk_hidden_fee",
            SAMPLE_CLAUSE_RISK_HIDDEN_FEE,
            {"monthly_rent": 950.0, "deposit_amount": 950.0},
        ),
        (
            "sample_clause_risk_access_notice",
            SAMPLE_CLAUSE_RISK_ACCESS_NOTICE,
            {"monthly_rent": 950.0, "deposit_amount": 950.0},
        ),
        (
            "sample_clause_risk_tenant_repairs",
            SAMPLE_CLAUSE_RISK_TENANT_REPAIRS,
            {"monthly_rent": 880.0, "deposit_amount": 880.0},
        ),
        # Part 10：合同完整性检查收尾（completeness_score / overall_status 刻意分层）
        (
            "sample_completeness_very_complete",
            SAMPLE_COMPLETENESS_VERY_COMPLETE,
            {"monthly_rent": 950.0, "deposit_amount": 1095.0},
        ),
        (
            "sample_completeness_missing_notice_repair",
            SAMPLE_COMPLETENESS_MISSING_NOTICE_REPAIR,
            {"monthly_rent": 1200.0, "deposit_amount": 1200.0},
        ),
        (
            "sample_completeness_missing_deposit_access",
            SAMPLE_COMPLETENESS_MISSING_DEPOSIT_ACCESS,
            {"monthly_rent": 950.0, "deposit_amount": 1095.0},
        ),
        (
            "sample_completeness_short_incomplete",
            SAMPLE_COMPLETENESS_SHORT_INCOMPLETE,
            {"monthly_rent": 500.0, "deposit_amount": 500.0},
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

# Part 8：clause-risk 专项样例应命中的 rule_id（与 ``clause_risk_map`` 中 risk_title 对应）
_CLAUSE_RISK_SAMPLES_EXPECT_RULE: dict[str, str] = {
    "sample_clause_risk_deposit_high": "deposit_amount_high",
    "sample_clause_risk_hidden_fee": "fee_suspicious_generic",
    "sample_clause_risk_access_notice": "landlord_enter_anytime",
    "sample_clause_risk_tenant_repairs": "tenant_all_repairs",
}


def _risk_title_for_rule_id(risks: list[Any], rule_id: str) -> str:
    rid = (rule_id or "").strip()
    for r in risks:
        if not isinstance(r, dict):
            continue
        if str(r.get("rule_id") or "").strip() == rid:
            return str(r.get("title") or "").strip()
    return ""


def _clause_risk_specs() -> list[tuple[str, str, dict[str, Any]]]:
    """Part 8 条款—风险联动专项样例。"""
    return [
        (k, v, w)
        for (k, v, w) in _sample_specs()
        if k in _CLAUSE_RISK_SAMPLES_EXPECT_RULE
    ]


def _clause_type_specs() -> list[tuple[str, str, dict[str, Any]]]:
    """Part 7 条款类型专项样例。"""
    return [
        (k, v, w)
        for (k, v, w) in _sample_specs()
        if k in _CLAUSE_TYPE_SAMPLES_EXPECT
    ]


def _severity_sample_specs() -> list[tuple[str, str, dict[str, Any]]]:
    """Part 9：条款风险强度（clause_severity_summary / clause_severity_overview）专项样例。"""
    return [
        (
            "sample_severity_one_clause_multi_high",
            SAMPLE_SEVERITY_ONE_CLAUSE_MULTI_HIGH,
            {"monthly_rent": 900.0, "deposit_amount": 900.0},
        ),
        (
            "sample_severity_mixed_clauses",
            SAMPLE_SEVERITY_MIXED_CLAUSES,
            {"monthly_rent": 950.0, "deposit_amount": 950.0},
        ),
        (
            "sample_severity_medium_fee_clause",
            SAMPLE_SEVERITY_MEDIUM_FEE_CLAUSE,
            {"monthly_rent": 880.0, "deposit_amount": 880.0},
        ),
        (
            "sample_severity_low_incomplete_clause",
            SAMPLE_SEVERITY_LOW_INCOMPLETE_CLAUSE,
            {"monthly_rent": 850.0, "deposit_amount": 850.0},
        ),
    ]


def validate_contract_severity_samples() -> None:
    """
    Part 9：``clause_severity_summary`` / ``clause_severity_overview`` 稳定存在、分值可预期、降序排序、与 explain 对齐。
    """
    for label, text, kwargs in _severity_sample_specs():
        out = analyze_contract_with_explain(contract_text=text, **kwargs)
        sa = out["structured_analysis"]
        ex = out["explain"]
        assert isinstance(sa.get("clause_severity_summary"), list), label
        assert isinstance(ex.get("clause_severity_overview"), list), label
        _assert_clause_severity_summary_shape(sa, label)
        _assert_contract_completeness_shape(sa, label)
        _assert_clause_severity_overview_explain(ex, label)
        _assert_clause_severity_score_descending(sa, label)
        _assert_clause_severity_explain_aligned(sa, ex, label)

        css = sa.get("clause_severity_summary") or []
        assert len(css) >= 1, f"{label}: clause_severity_summary 非空"

        if label == "sample_severity_one_clause_multi_high":
            assert len(css) == 1, label
            row0 = css[0] if isinstance(css[0], dict) else {}
            assert str(row0.get("clause_id") or "") == "clause_1", label
            assert int(row0.get("severity_score") or 0) >= 15, label
            assert int(row0.get("linked_risk_count") or 0) >= 5, label

        elif label == "sample_severity_mixed_clauses":
            assert len(css) >= 4, label
            scores = [int(x.get("severity_score") or 0) for x in css if isinstance(x, dict)]
            assert max(scores) - min(scores) >= 2, f"{label}: 分数未拉开 {scores!r}"

        elif label == "sample_severity_medium_fee_clause":
            assert len(css) == 1, label
            r0 = css[0] if isinstance(css[0], dict) else {}
            assert str(r0.get("highest_severity") or "") == "medium", label

        elif label == "sample_severity_low_incomplete_clause":
            assert len(css) == 1, label
            r0 = css[0] if isinstance(css[0], dict) else {}
            assert int(r0.get("severity_score") or 0) == 2, label


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
        _assert_clause_risk_map_shape(sa, label)
        _assert_clause_severity_summary_shape(sa, label)
        _assert_contract_completeness_shape(sa, label)
        assert isinstance(sa.get("risk_category_summary"), list), label
        assert isinstance(sa.get("risk_category_groups"), list), label
        assert isinstance(ex.get("risk_category_summary"), list), label
        assert isinstance(ex.get("risk_category_groups"), list), label
        assert isinstance(ex.get("clause_overview"), list), label
        _assert_clause_risk_overview_explain(ex, label)
        _assert_clause_severity_overview_explain(ex, label)
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
        _assert_clause_risk_map_shape(sa, label)
        _assert_clause_severity_summary_shape(sa, label)
        _assert_contract_completeness_shape(sa, label)
        assert isinstance(ex.get("clause_overview"), list), label
        _assert_clause_risk_overview_explain(ex, label)
        _assert_clause_severity_overview_explain(ex, label)
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


def validate_contract_clause_risk_samples() -> None:
    """Part 8：条款—风险联动专项样例命中预期 rule，且 ``clause_risk_map`` / ``clause_risk_overview`` 非空且结构稳定。"""
    for label, text, kwargs in _clause_risk_specs():
        out = analyze_contract_with_explain(contract_text=text, **kwargs)
        sa = out["structured_analysis"]
        ex = out["explain"]
        expected_rid = _CLAUSE_RISK_SAMPLES_EXPECT_RULE[label]
        risks = sa.get("risks") or []
        assert any(
            str(r.get("rule_id") or "").strip() == expected_rid
            for r in risks
            if isinstance(r, dict)
        ), label
        exp_title = _risk_title_for_rule_id(risks, expected_rid)
        assert exp_title, label
        crm = sa.get("clause_risk_map")
        assert isinstance(crm, list), label
        assert len(crm) >= 1, label
        _assert_clause_risk_map_shape(sa, label)
        _assert_clause_severity_summary_shape(sa, label)
        _assert_contract_completeness_shape(sa, label)
        titles_in_map = {str(x.get("risk_title") or "").strip() for x in crm if isinstance(x, dict)}
        assert exp_title in titles_in_map, f"{label}: expected title {exp_title!r} in {titles_in_map!r}"
        cro = ex.get("clause_risk_overview")
        assert isinstance(cro, list), label
        assert len(cro) >= 1, label
        _assert_clause_risk_overview_explain(ex, label)
        _assert_clause_severity_overview_explain(ex, label)
        for block in cro:
            if not isinstance(block, dict):
                continue
            lr = block.get("linked_risks")
            assert isinstance(lr, list), label
            for x in lr:
                if isinstance(x, dict):
                    assert isinstance(x.get("matched_keyword"), str), label


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
        _assert_clause_risk_map_shape(sa, label)
        _assert_clause_severity_summary_shape(sa, label)
        _assert_contract_completeness_shape(sa, label)
        _assert_contract_completeness_overview_explain(ex, sa, label)
        _assert_completeness_finale_expectations(sa, ex, label)
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
        _assert_clause_risk_overview_explain(ex, label)
        _assert_clause_severity_overview_explain(ex, label)
        assert len(ex["risk_category_groups"]) == len(ex["risk_category_summary"])
        pres = out.get("presentation") or {}
        sec_ids = [s.get("id") for s in (pres.get("sections") or []) if isinstance(s, dict)]
        assert "clause_overview" in sec_ids, label
        assert "clause_risk_overview" in sec_ids, label
        assert "clause_severity_overview" in sec_ids, label
        assert "contract_completeness_overview" in sec_ids, label
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
        _assert_clause_risk_map_shape(sa, label)
        _assert_clause_severity_summary_shape(sa, label)
        _assert_contract_completeness_shape(sa, label)
        _assert_contract_completeness_overview_explain(ex, sa, label)
        assert isinstance(sa.get("risk_category_groups"), list), label
        assert isinstance(sa.get("risk_category_summary"), list), label
        assert isinstance(ex.get("risk_category_groups"), list), label
        assert isinstance(ex.get("risk_category_summary"), list), label
        assert isinstance(ex.get("clause_overview"), list), label
        _assert_clause_risk_overview_explain(ex, label)
        _assert_clause_severity_overview_explain(ex, label)
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
    assert isinstance(sa.get("clause_risk_map"), list)
    assert sa.get("clause_risk_map") == []
    assert isinstance(sa.get("clause_severity_summary"), list)
    assert sa.get("clause_severity_summary") == []
    assert isinstance(ex.get("clause_overview"), list)
    assert ex.get("clause_overview") == []
    assert isinstance(ex.get("clause_risk_overview"), list)
    assert ex.get("clause_risk_overview") == []
    assert isinstance(ex.get("clause_severity_overview"), list)
    assert ex.get("clause_severity_overview") == []
    _assert_contract_completeness_shape(sa, "empty_contract_text")
    _assert_contract_completeness_overview_explain(ex, sa, "empty_contract_text")


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
    assert isinstance(sa.get("clause_risk_map"), list)
    assert sa.get("clause_risk_map") == []
    assert isinstance(sa.get("clause_severity_summary"), list)
    assert sa.get("clause_severity_summary") == []
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
    assert isinstance(ex.get("clause_risk_overview"), list)
    assert isinstance(ex.get("clause_severity_overview"), list)
    assert ex.get("clause_severity_overview") == []
    _assert_contract_completeness_shape(sa, "empty_risk_fallback")
    assert len(ex["clause_overview"]) >= 1


def test_contract_analysis_samples() -> None:
    """与项目 ``test_*.py`` 风格兼容：可直接被 pytest 收集。"""
    validate_contract_analysis_samples()
    validate_contract_localization_samples()
    validate_contract_category_samples()
    validate_contract_clause_type_samples()
    validate_contract_clause_risk_samples()
    validate_contract_severity_samples()
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
        print("【clause_risk_overview】")
        for block in ex.get("clause_risk_overview") or []:
            if isinstance(block, dict):
                print(
                    f"  · {block.get('clause_id')} [{block.get('clause_type')}] "
                    f"{block.get('short_clause_preview')}"
                )
                for lr in block.get("linked_risks") or []:
                    if isinstance(lr, dict):
                        sr = str(lr.get("short_reason") or "")
                        tail = (sr[:72] + "…") if len(sr) > 72 else sr
                        print(
                            f"      - {lr.get('risk_title')} [{lr.get('risk_category')}] "
                            f"sev={lr.get('severity')} kw={lr.get('matched_keyword')!r} | {tail}"
                        )
        if not (ex.get("clause_risk_overview") or []):
            print("  (none)")
        print()
        print("【clause_severity_overview】")
        for row in ex.get("clause_severity_overview") or []:
            if isinstance(row, dict):
                titles = row.get("linked_risk_titles") or []
                ts = "; ".join(str(t) for t in titles if str(t).strip()) or "—"
                print(
                    f"  · {row.get('clause_id')} [{row.get('clause_type')}] "
                    f"score={row.get('severity_score')} highest={row.get('highest_severity')} "
                    f"n={row.get('linked_risk_count')} | {row.get('short_clause_preview')}"
                )
                print(f"      titles: {ts}")
        if not (ex.get("clause_severity_overview") or []):
            print("  (none)")
        print()
        print("【contract_completeness_overview】")
        cco = ex.get("contract_completeness_overview")
        if isinstance(cco, dict):
            print(f"  overall_status: {cco.get('overall_status')}")
            print(f"  completeness_score: {cco.get('completeness_score')}")
            for m in cco.get("missing_core_items") or []:
                print(f"  - missing: {m}")
            if not (cco.get("missing_core_items") or []):
                print("  missing_core_items: (none)")
            for u in cco.get("unclear_items") or []:
                print(f"  - unclear: {u}")
            if not (cco.get("unclear_items") or []):
                print("  unclear_items: (none)")
            ss = str(cco.get("short_summary") or "—")
            print(f"  short_summary: {ss[:400]}{'…' if len(ss) > 400 else ''}")
        else:
            print("  (invalid)")
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
