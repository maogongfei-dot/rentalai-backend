"""
Contract analysis entry: run pipeline and print envelope (Phase 3 Part 26).
"""

from __future__ import annotations

from typing import Any

from modules.contract.contract_presenter import print_contract_result
from modules.contract.contract_service import run_contract_analysis


def handle_contract_input(text: str) -> dict[str, Any]:
    """
    Run contract analysis and print the standard result block.

    Empty ``text`` is passed through to ``run_contract_analysis`` unchanged.
    """
    final_output = run_contract_analysis(text)
    print_contract_result(final_output)
    return final_output
