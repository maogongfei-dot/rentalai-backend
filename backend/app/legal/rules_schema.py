"""Legal rule data structures (Phase 0 compliance rules library)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class RuleCheckExample:
    trigger_keywords: list[str]
    compliant_example: str
    risky_example: str


@dataclass
class LegalRule:
    rule_id: str
    category: str
    title: str
    jurisdiction: str
    effective_from: str
    summary_plain: str
    legal_status_logic: str
    risk_logic: str
    key_points: list[str]
    red_flags: list[str]
    examples: list[RuleCheckExample]
    disclaimer_required: bool = True


@dataclass
class LegalRuleSet:
    ruleset_id: str
    jurisdiction: str
    version_label: str
    effective_from: str
    rules: dict[str, LegalRule]

    def get_rule(self, rule_id: str) -> LegalRule | None:
        return self.rules.get(rule_id)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ruleset_id": self.ruleset_id,
            "jurisdiction": self.jurisdiction,
            "version_label": self.version_label,
            "effective_from": self.effective_from,
            "rules": {rid: asdict(rule) for rid, rule in self.rules.items()},
        }
