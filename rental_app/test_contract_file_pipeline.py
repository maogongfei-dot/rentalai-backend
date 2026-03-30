# Phase 3：文件路径 → 合同分析 pipeline 最小测试
# 运行：cd rental_app && pytest test_contract_file_pipeline.py -q
# 或：python -c "from contract_analysis.demo_contract_document_readers import test_contract_document_readers; test_contract_document_readers()"

from __future__ import annotations

from contract_analysis.demo_contract_file_analysis import validate_contract_file_analysis_demo


def test_contract_file_analysis_pipeline():
    """向后兼容：等同 ``test_contract_document_readers``（固定 ``samples/sample_contract.*``）。"""
    validate_contract_file_analysis_demo()
