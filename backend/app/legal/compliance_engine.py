"""Local rule-based legal compliance analysis (no external models or DB)."""

from __future__ import annotations

import re
from typing import Iterable

from .compliance_types import ComplianceAnalysisResult, LegalInput, RuleEvaluation
from .rules_registry import get_ruleset
from .rules_schema import LegalRule

_RISK_HIGH = "high"
_RISK_MEDIUM = "medium"
_RISK_LOW = "low"

_DISCLAIMER = (
    "This result is general information only and is not legal advice. "
    "RentalAI is not a law firm and does not replace a qualified solicitor or housing adviser."
)

# Coarse keywords for auto-detection of which rules apply to a clause.
_RULE_DETECTION_KEYWORDS: dict[str, list[str]] = {
    "deposit": [
        "deposit",
        "tenancy deposit",
        "deposit protection",
        "dps",
        "mydeposits",
        "tds",
        "scheme",
        "prescribed information",
    ],
    "notice": [
        "notice",
        "section 21",
        "section 8",
        "two months",
        "termination notice",
        "quit",
        "possession",
    ],
    "rent_increase": [
        "rent increase",
        "rent review",
        "increase rent",
        "review clause",
        "cpi",
        "rpi",
        "market rent",
    ],
    "access": [
        "access",
        "entry",
        "inspect",
        "inspection",
        "quiet enjoyment",
        "landlord enter",
        "keys",
        "24 hours",
        "48 hours",
    ],
    "repairs": [
        "repair",
        "maintenance",
        "boiler",
        "heating",
        "structure",
        "damp",
        "electrics",
        "plumbing",
        "landlord repair",
        "tenant repair",
    ],
    "termination": [
        "termination",
        "terminate",
        "break clause",
        "early termination",
        "forfeiture",
        "end of tenancy",
        "fixed term",
        "surrender",
    ],
}


def normalize_text(text: str) -> str:
    """Lowercase, collapse whitespace, strip."""
    if not text:
        return ""
    s = text.strip().lower()
    s = re.sub(r"\s+", " ", s)
    return s


def build_disclaimer() -> str:
    return _DISCLAIMER


def _significant_words(phrase: str) -> list[str]:
    return [w for w in re.findall(r"[a-z0-9]+", phrase.lower()) if len(w) >= 4]


def _phrase_matches_text(text_norm: str, phrase: str) -> bool:
    words = _significant_words(phrase)
    if not words:
        return False
    hits = sum(1 for w in words if w in text_norm)
    need = max(1, min(len(words), (len(words) + 1) // 2))
    return hits >= need


def _match_phrase_list(text_norm: str, phrases: Iterable[str]) -> list[str]:
    return [p for p in phrases if _phrase_matches_text(text_norm, p)]


def _collect_trigger_keywords(rule: LegalRule) -> list[str]:
    out: list[str] = []
    for ex in rule.examples:
        out.extend(ex.trigger_keywords)
    return out


def _any_trigger_hit(text_norm: str, keywords: list[str]) -> bool:
    for kw in keywords:
        k = normalize_text(kw)
        if not k:
            continue
        if k in text_norm:
            return True
    return False


def detect_relevant_rules(text: str) -> list[str]:
    """Keyword-based coarse detection of which rule ids may apply."""
    text_norm = normalize_text(text)
    if not text_norm:
        return []
    found: list[str] = []
    for rule_id, kws in _RULE_DETECTION_KEYWORDS.items():
        for kw in kws:
            if normalize_text(kw) in text_norm:
                found.append(rule_id)
                break
    return found


def evaluate_against_rule(text: str, rule: LegalRule) -> RuleEvaluation:
    """Match clause text against rule red flags, key points, and example keywords."""
    text_norm = normalize_text(text)
    triggers = _collect_trigger_keywords(rule)
    matched_red = _match_phrase_list(text_norm, rule.red_flags)
    matched_kp = _match_phrase_list(text_norm, rule.key_points)
    trigger_hit = _any_trigger_hit(text_norm, triggers)

    has_signal = bool(matched_red or matched_kp or trigger_hit)
    if not text_norm.strip():
        return RuleEvaluation(
            rule_id=rule.rule_id,
            title=rule.title,
            is_legal=None,
            risk_level=_RISK_MEDIUM,
            explanation_plain=(
                "No text was provided, so this rule could not be checked against your clause."
            ),
            matched_red_flags=[],
            matched_key_points=[],
            confidence=0.2,
        )

    if not has_signal:
        return RuleEvaluation(
            rule_id=rule.rule_id,
            title=rule.title,
            is_legal=None,
            risk_level=_RISK_MEDIUM,
            explanation_plain=(
                f"This clause does not clearly mention topics covered by “{rule.title}”. "
                "There is not enough here to say whether it complies."
            ),
            matched_red_flags=[],
            matched_key_points=[],
            confidence=0.35,
        )

    if matched_red:
        conf = min(0.95, 0.55 + 0.08 * len(matched_red))
        explanation_plain = (
            f"The wording appears to touch issues this rule flags as risky ({len(matched_red)} "
            f"match(es)). Treat the clause as potentially problematic until a professional reviews it."
        )
        return RuleEvaluation(
            rule_id=rule.rule_id,
            title=rule.title,
            is_legal=False,
            risk_level=_RISK_HIGH,
            explanation_plain=explanation_plain,
            matched_red_flags=matched_red,
            matched_key_points=matched_kp,
            confidence=conf,
        )

    if matched_kp or trigger_hit:
        conf = min(0.9, 0.5 + 0.05 * (len(matched_kp) + (1 if trigger_hit else 0)))
        risk = _RISK_LOW if len(matched_kp) >= 2 or (trigger_hit and matched_kp) else _RISK_MEDIUM
        explanation_plain = (
            f"The clause relates to “{rule.title}” and lines up with some expected points, "
            "but no strong warning patterns from this checklist were found. A quick professional "
            "check is still sensible for important contracts."
        )
        return RuleEvaluation(
            rule_id=rule.rule_id,
            title=rule.title,
            is_legal=True,
            risk_level=risk,
            explanation_plain=explanation_plain,
            matched_red_flags=[],
            matched_key_points=matched_kp,
            confidence=conf,
        )


def compute_overall_result(
    rule_results: list[RuleEvaluation],
) -> tuple[bool | None, str, str]:
    """Derive overall legality flag, risk band, and one-line summary."""
    if not rule_results:
        return (
            None,
            _RISK_MEDIUM,
            "No rules were evaluated, so no overall compliance picture is available.",
        )

    any_false = any(r.is_legal is False for r in rule_results)
    any_true = any(r.is_legal is True for r in rule_results)
    all_none = all(r.is_legal is None for r in rule_results)

    if any_false:
        overall_legal: bool | None = False
    elif all_none:
        overall_legal = None
    elif any_true:
        overall_legal = True
    else:
        overall_legal = None

    levels = [r.risk_level for r in rule_results]
    if _RISK_HIGH in levels:
        overall_risk = _RISK_HIGH
    elif _RISK_MEDIUM in levels:
        overall_risk = _RISK_MEDIUM
    else:
        overall_risk = _RISK_LOW

    if overall_risk == _RISK_HIGH:
        summary = (
            "At least one area looks high risk from automated checks; get the wording reviewed "
            "before you rely on it."
        )
    elif overall_legal is False:
        summary = (
            "Some clauses look problematic against the checklist; treat the contract with caution "
            "until a professional has checked it."
        )
    elif overall_legal is None:
        summary = (
            "The automated check could not confirm compliance overall; you may need more detail "
            "or expert advice."
        )
    else:
        summary = (
            "Nothing in this pass triggered the strongest warnings, but this is still only a "
            "rough screen—not a clean bill of health."
        )

    return overall_legal, overall_risk, summary


def analyze_legal_compliance(payload: LegalInput) -> ComplianceAnalysisResult:
    ruleset = get_ruleset(
        jurisdiction=payload.jurisdiction,
        target_date=payload.target_date,
    )
    j = ruleset.jurisdiction

    if payload.rule_ids:
        ids = [rid for rid in payload.rule_ids if rid in ruleset.rules]
    else:
        ids = detect_relevant_rules(payload.text)
        if not ids:
            ids = list(ruleset.rules.keys())

    rule_results: list[RuleEvaluation] = []
    for rid in ids:
        rule = ruleset.rules.get(rid)
        if rule is None:
            continue
        rule_results.append(evaluate_against_rule(payload.text, rule))

    overall_legal, overall_risk, summary_plain = compute_overall_result(rule_results)

    return ComplianceAnalysisResult(
        jurisdiction=j,
        target_date=payload.target_date,
        source_type=payload.source_type,
        overall_is_legal=overall_legal,
        overall_risk_level=overall_risk,
        summary_plain=summary_plain,
        disclaimer=build_disclaimer(),
        rule_results=rule_results,
    )
