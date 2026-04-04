"""Registry of legal rule sets by jurisdiction and effective date."""

from __future__ import annotations

from .rules_england_current import build_england_current_ruleset
from .rules_england_post_2026_05_01 import build_england_post_2026_ruleset
from .rules_schema import LegalRule, LegalRuleSet

_ENGLAND_JURISDICTION = "england"


def get_all_rulesets() -> dict[str, LegalRuleSet]:
    return {
        "england_current": build_england_current_ruleset(),
        "england_post_2026_05_01": build_england_post_2026_ruleset(),
    }


def get_ruleset(jurisdiction: str = "england", target_date: str | None = None) -> LegalRuleSet:
    if jurisdiction.lower() != _ENGLAND_JURISDICTION:
        jurisdiction = _ENGLAND_JURISDICTION
    if target_date is None:
        return build_england_current_ruleset()
    td = str(target_date).strip()
    if td >= "2026-05-01":
        return build_england_post_2026_ruleset()
    return build_england_current_ruleset()


def get_rule(
    rule_id: str,
    jurisdiction: str = "england",
    target_date: str | None = None,
) -> LegalRule | None:
    rs = get_ruleset(jurisdiction=jurisdiction, target_date=target_date)
    return rs.get_rule(rule_id)
