"""Contract analysis page structure (data only; no analysis engine or uploads)."""

_HERO_SECTION = {
    "title": "AI Contract Risk Analysis",
    "subtitle": "Check rental contracts before you sign",
}

_INPUT_SECTION = {
    "text_input": {},
    "file_upload": {},
    "example_contract_button": {},
}

_RESULT_SECTIONS = [
    "risk_summary",
    "legal_explanation",
    "action_plan",
    "missing_clauses",
    "communication_template",
]

_ACTIONS = [
    "Analyze Contract",
    "Save Result",
    "Download Report",
    "Back to Home",
]


def get_contract_page_structure() -> dict:
    """Return the canonical contract analysis page layout for downstream UI."""
    return {
        "page_type": "contract_analysis",
        "hero_section": dict(_HERO_SECTION),
        "input_section": {k: dict(v) for k, v in _INPUT_SECTION.items()},
        "result_sections": list(_RESULT_SECTIONS),
        "actions": list(_ACTIONS),
    }
