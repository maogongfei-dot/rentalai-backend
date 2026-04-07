"""
Contract analysis entry: run pipeline and print envelope (Phase 3 Part 26).
"""

from __future__ import annotations

from typing import Any

from modules.contract.contract_presenter import print_contract_result
from modules.contract.contract_service import run_contract_analysis


def handle_contract_input(text: str, *, print_result: bool = True) -> dict[str, Any]:
    """
    Run contract analysis and print the standard result block.

    Empty ``text`` is passed through to ``run_contract_analysis`` unchanged.
    Returns the same ``final_output`` dict (ok, module, summary, details, actions,
    missing_clauses, flagged_clauses, verdict, human_* fields, ``final_display``,
    analysis_completeness / missing_information / human_missing_info_guidance,
    recommended_decision / direct_answer / direct_answer_short,
    result_confidence / confidence_reason / human_confidence_notice,
    urgency_level / urgency_reason / priority_actions / human_urgency_notice,
    supporting_factors / blocking_factors / key_decision_drivers / human_decision_factors_notice, error)
    for callers / main system wiring.

    ``print_result=False`` skips printing so callers can enrich ``final_display`` (e.g. meta) first.
    """
    final_output = run_contract_analysis(text)
    if print_result:
        print_contract_result(final_output)
    return final_output
