"""England tenancy rules — version 'current' (effective 2026-04-04)."""

from __future__ import annotations

from .rules_schema import LegalRule, LegalRuleSet, RuleCheckExample


def build_england_current_ruleset() -> LegalRuleSet:
    rules: dict[str, LegalRule] = {
        "deposit": LegalRule(
            rule_id="deposit",
            category="deposit_and_tenancy_deposit_protection",
            title="Tenancy deposits and deposit protection (England)",
            jurisdiction="england",
            effective_from="2026-04-04",
            summary_plain=(
                "In England, most assured shorthold tenancy (AST) deposits must be protected in a "
                "government-approved scheme within a statutory time limit; caps apply to the amount "
                "that can be taken as a tenancy deposit."
            ),
            legal_status_logic=(
                "If the tenancy is an AST (or otherwise within scope), the deposit must not exceed "
                "the applicable cap (typically five weeks' rent where annual rent is below a "
                "threshold, otherwise six weeks). Deposit must be protected and prescribed "
                "information provided; non-compliance affects validity of certain notices and may "
                "expose the landlord to penalties."
            ),
            risk_logic=(
                "HIGH if deposit exceeds the statutory cap for the tenancy type, or if there is no "
                "evidence of protection within the required period. MEDIUM if protection status is "
                "unclear from the contract alone."
            ),
            key_points=[
                "Check deposit amount against weekly rent to assess cap compliance.",
                "Confirm protection scheme and prescribed information (contract may reference this).",
                "Unprotected or late-protected deposits are a compliance risk, not just a drafting issue.",
            ],
            red_flags=[
                "Deposit stated above five/six weeks of rent (as applicable) without lawful exception.",
                "Clause stating deposit need not be protected or will be 'held informally' only.",
                "No mention of scheme or timing when an AST is indicated.",
            ],
            examples=[
                RuleCheckExample(
                    trigger_keywords=["deposit", "five weeks", "DPS", "protection"],
                    compliant_example=(
                        "Deposit £1,200 (5 weeks at £240/week) — to be protected with Scheme X within 30 days."
                    ),
                    risky_example=(
                        "Deposit £3,000 for the same weekly rent with no scheme reference — likely over cap "
                        "and/or unprotected."
                    ),
                ),
            ],
            disclaimer_required=True,
        ),
        "notice": LegalRule(
            rule_id="notice",
            category="notice_periods_and_grounds",
            title="Notice periods — baseline checks (England)",
            jurisdiction="england",
            effective_from="2026-04-04",
            summary_plain=(
                "Whether a notice period is lawful depends on tenancy type, stage of tenancy, and "
                "which notice is used (e.g. Section 21 vs Section 8). This module provides baseline "
                "prompts and risk flags only."
            ),
            legal_status_logic=(
                "Validate notice type against tenancy; minimum periods and form requirements differ. "
                "Grounds for possession under Section 8 are enumerated in statute — complex cases "
                "require case-by-case review (placeholder for extended rules)."
            ),
            risk_logic=(
                "HIGH if contract imposes very short tenant notice without statutory basis or "
                "conflicts with mandatory wording. MEDIUM if notice clauses are vague or one-sided."
            ),
            key_points=[
                "Identify tenancy type (e.g. AST) before assessing notice clauses.",
                "Landlord and tenant notice obligations are not always symmetrical.",
                "Reserved extension slot: grounds-based Section 8 schedules (future ruleset version).",
            ],
            red_flags=[
                "Clause claiming 'immediate termination' without statutory process.",
                "Tenant notice period far shorter than common statutory minima for the stated tenancy type.",
            ],
            examples=[
                RuleCheckExample(
                    trigger_keywords=["notice", "two months", "Section 21"],
                    compliant_example=(
                        "Landlord gives two months' notice in prescribed form where Section 21 prerequisites are met."
                    ),
                    risky_example=(
                        "'Landlord may end tenancy with 7 days notice' for an AST — likely inconsistent with baseline requirements."
                    ),
                ),
            ],
            disclaimer_required=True,
        ),
        "rent_increase": LegalRule(
            rule_id="rent_increase",
            category="rent_review_and_increases",
            title="Rent increases and review clauses (England)",
            jurisdiction="england",
            effective_from="2026-04-04",
            summary_plain=(
                "Rent increases must follow the tenancy agreement and statute (e.g. frequency, form "
                "of notice, and whether a rent review or renewal process applies)."
            ),
            legal_status_logic=(
                "If a rent review clause exists, assess clarity of formula, frequency, and dispute "
                "mechanism. Statutory restrictions may apply to certain periodic tenancies; "
                "exceptional increases may require human review."
            ),
            risk_logic=(
                "HIGH if open-ended or unilateral increases without clear limits or notice. MEDIUM "
                "if review clause is ambiguous or references external indices without definition."
            ),
            key_points=[
                "Flag presence or absence of an express rent review clause.",
                "Compare proposed increase to market and clause caps (heuristic only).",
                "Escalate for manual review when increase timing conflicts with fixed term or statute.",
            ],
            red_flags=[
                "Unlimited rent increase at landlord discretion with no notice period.",
                "Retroactive rent uplift without agreement or statutory basis stated.",
            ],
            examples=[
                RuleCheckExample(
                    trigger_keywords=["rent increase", "review", "RPI"],
                    compliant_example=(
                        "Annual increase by CPI + 1% with 60 days' written notice as per clause 5."
                    ),
                    risky_example=(
                        "Landlord may set new rent at any amount monthly — no cap or process stated."
                    ),
                ),
            ],
            disclaimer_required=True,
        ),
        "access": LegalRule(
            rule_id="access",
            category="landlord_access_and_quiet_enjoyment",
            title="Landlord access and tenant quiet enjoyment (England)",
            jurisdiction="england",
            effective_from="2026-04-04",
            summary_plain=(
                "Tenants have the right to quiet enjoyment; landlords generally need reasonable "
                "notice to enter except in emergencies."
            ),
            legal_status_logic=(
                "Access for repairs or inspection typically requires reasonable notice (often "
                "24–48 hours unless agreed otherwise) and a lawful purpose. Emergency access may be "
                "narrow (e.g. gas leak, major water ingress)."
            ),
            risk_logic=(
                "HIGH if contract allows entry at any time without notice or purpose. MEDIUM if "
                "notice periods are unclear."
            ),
            key_points=[
                "Distinguish routine access vs emergency.",
                "Repeated intrusive access may breach quiet enjoyment even if nominally 'allowed' by a one-sided clause.",
            ],
            red_flags=[
                "Landlord may enter without notice for non-emergencies.",
                "Tenant waives all rights to object to access.",
            ],
            examples=[
                RuleCheckExample(
                    trigger_keywords=["access", "inspection", "24 hours"],
                    compliant_example=(
                        "Landlord to give at least 24 hours' written notice for non-emergency visits except by agreement."
                    ),
                    risky_example=(
                        "Landlord retains keys and may enter at any time without notice for 'inspections'."
                    ),
                ),
            ],
            disclaimer_required=True,
        ),
        "repairs": LegalRule(
            rule_id="repairs",
            category="repairing_obligations",
            title="Repairing obligations — structure, services, safety (England)",
            jurisdiction="england",
            effective_from="2026-04-04",
            summary_plain=(
                "Landlords are generally responsible for keeping the structure and exterior, and "
                "installations for supply of water, gas, electricity, sanitation, and space heating "
                "in repair; tenants usually handle damage they cause and minor tenant obligations "
                "if clearly stated."
            ),
            legal_status_logic=(
                "Assess whether repair obligations are allocated consistently with overriding "
                "landlord duties for core building and systems; tenant cannot be made solely "
                "responsible for landlord statutory repair functions."
            ),
            risk_logic=(
                "HIGH if all repairs including structural and heating are pushed to tenant. MEDIUM "
                "if demarcation is vague for essential systems."
            ),
            key_points=[
                "Core systems (heating, hot water, electrics, structure) — landlord baseline duty.",
                "Cosmetic damage and tenant misuse — often tenant liability if clearly drafted.",
            ],
            red_flags=[
                "Tenant responsible for all repairs including roof, boiler, and electrics without carve-out.",
                "Waiver of fitness for habitation or statutory repair duties.",
            ],
            examples=[
                RuleCheckExample(
                    trigger_keywords=["repairs", "boiler", "structure"],
                    compliant_example=(
                        "Landlord responsible for external structure and heating/hot water systems; tenant for damage caused wilfully."
                    ),
                    risky_example=(
                        "Tenant shall maintain and replace all parts of the property including roof and boiler at tenant cost."
                    ),
                ),
            ],
            disclaimer_required=True,
        ),
        "termination": LegalRule(
            rule_id="termination",
            category="termination_and_break_clauses",
            title="Termination, break clauses, and fairness (England)",
            jurisdiction="england",
            effective_from="2026-04-04",
            summary_plain=(
                "Ending a tenancy follows contract terms and statutory processes (notice, grounds, "
                "and protection for tenants). Break clauses and early termination fees must be "
                "clear and not punitive beyond lawful bounds."
            ),
            legal_status_logic=(
                "Assess symmetry of break rights, notice lengths, and fees. One-sided landlord-only "
                "termination without statutory backing is suspect; vague 'landlord discretion' "
                "termination is high risk."
            ),
            risk_logic=(
                "HIGH if tenant has no break but landlord has broad early termination without grounds. "
                "MEDIUM if break fees are disproportionate or unclear."
            ),
            key_points=[
                "Check for mutual break vs landlord-only exit.",
                "Flag ambiguous 'material breach' definitions used only against tenant.",
            ],
            red_flags=[
                "Landlord may terminate at will; tenant locked for full term without break.",
                "Excessive early termination charges vs actual loss.",
            ],
            examples=[
                RuleCheckExample(
                    trigger_keywords=["break clause", "early termination", "forfeiture"],
                    compliant_example=(
                        "Either party may terminate on two months' notice after month 6, subject to rent paid to date."
                    ),
                    risky_example=(
                        "Landlord may end tenancy immediately if dissatisfied; tenant must pay 12 months' rent to leave early."
                    ),
                ),
            ],
            disclaimer_required=True,
        ),
    }
    return LegalRuleSet(
        ruleset_id="england_current",
        jurisdiction="england",
        version_label="current",
        effective_from="2026-04-04",
        rules=rules,
    )
