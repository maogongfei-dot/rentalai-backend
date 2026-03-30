"""
Phase 3：内置样例合同文本（从 ``contract_analysis/samples/*.txt`` 读取，便于单测与演示）。

若需修改样例，请直接编辑同目录下 .txt 文件。
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
