"""Phase 0 legal compliance rules library (England baseline + dated variants)."""

from __future__ import annotations

from .rules_registry import get_rule as get_rule
from .rules_registry import get_ruleset as get_ruleset
from .rules_schema import LegalRule, LegalRuleSet, RuleCheckExample

__all__ = [
    "LegalRule",
    "LegalRuleSet",
    "RuleCheckExample",
    "get_ruleset",
    "get_rule",
]
