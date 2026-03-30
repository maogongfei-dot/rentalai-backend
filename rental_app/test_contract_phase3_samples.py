# Phase 3 合同分析：样例合同最小测试（pytest 兼容）
# 运行：cd rental_app && pytest test_contract_phase3_samples.py -q
# 或：python -m contract_analysis.demo_contract_samples

from __future__ import annotations

from contract_analysis.demo_contract_samples import (
    validate_contract_analysis_empty_risk_fallback,
    validate_contract_analysis_samples,
    validate_contract_localization_samples,
)


def test_phase3_contract_analysis_samples():
    validate_contract_analysis_samples()


def test_phase3_contract_localization_samples():
    validate_contract_localization_samples()


def test_phase3_empty_risk_fallback():
    validate_contract_analysis_empty_risk_fallback()
