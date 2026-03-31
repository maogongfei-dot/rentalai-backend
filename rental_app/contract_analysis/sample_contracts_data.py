"""
Phase 3：内置样例合同文本（从 ``contract_analysis/samples/*.txt`` 读取，便于单测与演示）。

若需修改样例，请直接编辑同目录下 .txt 文件。

``sample_cat_*.txt``：Part 6 分类标签与分组汇总测试用短样例。

``sample_clause_*.txt``：Part 7 条款切分与 clause_type 多场景样例。

``sample_clause_risk_*.txt``：Part 8 条款—风险联动（clause_risk_map / clause_risk_overview）专项样例。
"""

from __future__ import annotations

from pathlib import Path

_SAMPLES_DIR = Path(__file__).resolve().parent / "samples"


def _load_sample(filename: str) -> str:
    p = _SAMPLES_DIR / filename
    return p.read_text(encoding="utf-8")


SAMPLE_CONTRACT_SAFE: str = _load_sample("sample_contract_safe.txt")
SAMPLE_CONTRACT_MEDIUM_RISK: str = _load_sample("sample_contract_medium_risk.txt")
SAMPLE_CONTRACT_HIGH_RISK: str = _load_sample("sample_contract_high_risk.txt")

SAMPLE_CONTRACT_DEPOSIT_HEAVY: str = _load_sample("sample_contract_deposit_heavy.txt")
SAMPLE_CONTRACT_MISSING_NOTICE_REPAIR: str = _load_sample("sample_contract_missing_notice_repair.txt")
SAMPLE_CONTRACT_UNFAIR_ENTRY: str = _load_sample("sample_contract_unfair_entry.txt")
SAMPLE_CONTRACT_HIDDEN_FEES_PENALTY: str = _load_sample("sample_contract_hidden_fees_penalty.txt")

# Part 5：条款定位专项样例（单句/段便于 matched_text 抽取）
SAMPLE_LOC_HIDDEN_FEE: str = _load_sample("sample_loc_hidden_fee.txt")
SAMPLE_LOC_LANDLORD_ACCESS: str = _load_sample("sample_loc_landlord_access.txt")
SAMPLE_LOC_TENANT_REPAIRS: str = _load_sample("sample_loc_tenant_repairs.txt")

# Part 6：风险分类 / 分组专项样例（各段刻意触发不同 risk_category）
SAMPLE_CAT_DEPOSIT_ISSUE: str = _load_sample("sample_cat_deposit_issue.txt")
SAMPLE_CAT_HIDDEN_FEE: str = _load_sample("sample_cat_hidden_fee.txt")
SAMPLE_CAT_ACCESS_NOTICE: str = _load_sample("sample_cat_access_notice.txt")
SAMPLE_CAT_RENT_TERMINATION: str = _load_sample("sample_cat_rent_termination.txt")

# Part 7：条款切分 + clause_type 识别专项（多编号条款、多 clause_type）
SAMPLE_CLAUSE_DEPOSIT_RENT: str = _load_sample("sample_clause_deposit_rent.txt")
SAMPLE_CLAUSE_NOTICE_TERMINATION: str = _load_sample("sample_clause_notice_termination.txt")
SAMPLE_CLAUSE_REPAIRS_BILLS: str = _load_sample("sample_clause_repairs_bills.txt")
SAMPLE_CLAUSE_PETS_SUBLETTING: str = _load_sample("sample_clause_pets_subletting.txt")

# Part 8：条款—风险联动专项（单条 clause 尽量对应单条风险规则）
SAMPLE_CLAUSE_RISK_DEPOSIT_HIGH: str = _load_sample("sample_clause_risk_deposit_high.txt")
SAMPLE_CLAUSE_RISK_HIDDEN_FEE: str = _load_sample("sample_clause_risk_hidden_fee.txt")
SAMPLE_CLAUSE_RISK_ACCESS_NOTICE: str = _load_sample("sample_clause_risk_access_notice.txt")
SAMPLE_CLAUSE_RISK_TENANT_REPAIRS: str = _load_sample("sample_clause_risk_tenant_repairs.txt")
