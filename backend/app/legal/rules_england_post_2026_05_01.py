"""England tenancy rules — version 'post_2026_05_01' (effective 2026-05-01, future-dated policy layer)."""

from __future__ import annotations

from .rules_schema import LegalRule, LegalRuleSet, RuleCheckExample


def build_england_post_2026_ruleset() -> LegalRuleSet:
    """Same six core rules as current; notice / termination / rent_increase text reflects post-2026-05-01 regime summaries."""
    rules: dict[str, LegalRule] = {
        "deposit": LegalRule(
            rule_id="deposit",
            category="deposit_and_tenancy_deposit_protection",
            title="Tenancy deposits and deposit protection (England)",
            jurisdiction="england",
            effective_from="2026-05-01",
            summary_plain=(
                "Deposit caps and protection requirements continue to apply; this ruleset version "
                "aligns with the 2026-05-01 effective date for cross-version testing (amounts and "
                "schemes unchanged at summary level — verify against live statute)."
            ),
            legal_status_logic=(
                "Assess cap (five/six weeks as applicable), protection in an approved scheme, and "
                "prescribed information. Non-compliance remains a high-severity compliance issue."
            ),
            risk_logic=(
                "HIGH when deposit exceeds cap or protection is absent/late. MEDIUM when documentation is incomplete."
            ),
            key_points=[
                "Cross-check weekly rent vs deposit amount.",
                "Confirm scheme name and timing on the face of the agreement.",
            ],
            red_flags=[
                "Deposit above statutory cap.",
                "No protection pathway described for an in-scope tenancy.",
            ],
            examples=[
                RuleCheckExample(
                    trigger_keywords=["deposit", "cap"],
                    compliant_example="Deposit within five weeks and scheme stated.",
                    risky_example="Deposit eight weeks of rent with no protection clause.",
                ),
            ],
            disclaimer_required=True,
        ),
        "notice": LegalRule(
            rule_id="notice",
            category="notice_periods_and_grounds",
            title="Notice periods — post-2026-05-01 summary layer (England)",
            jurisdiction="england",
            effective_from="2026-05-01",
            summary_plain=(
                "From 2026-05-01 this ruleset uses an updated **summary layer** for notice-related "
                "checks: emphasis on harmonised minimum notice prompts for automated review, while "
                "full statutory schedules remain external (placeholder for future ground-level rules)."
            ),
            legal_status_logic=(
                "Post-2026-05-01 logic (this version): flag shorter-than-baseline landlord notices for "
                "review; Section 21 / Section 8 distinction preserved; **extended grounds tables are "
                "reserved for a later rules pack** — do not infer full possession outcomes here."
            ),
            risk_logic=(
                "HIGH if stated notice period falls below the post-2026-05-01 baseline summary for the "
                "declared tenancy path. MEDIUM if notice type is unspecified."
            ),
            key_points=[
                "Use tenancy type + notice label to pick the baseline prompt set.",
                "Extension hook: import statutory ground lists when `version_label` >= post_2026_05_01.",
            ],
            red_flags=[
                "Notice period inconsistent with post-2026-05-01 baseline summary for AST-style paths.",
                "Conflated tenant/landlord notice duties in one ambiguous clause.",
            ],
            examples=[
                RuleCheckExample(
                    trigger_keywords=["notice", "2026-05-01", "Section 8"],
                    compliant_example=(
                        "Notice type stated with period matching baseline summary after 2026-05-01 for the chosen path."
                    ),
                    risky_example=(
                        "Landlord one-week notice for non-payment where baseline summary expects longer minimum."
                    ),
                ),
            ],
            disclaimer_required=True,
        ),
        "rent_increase": LegalRule(
            rule_id="rent_increase",
            category="rent_review_and_increases",
            title="Rent increases — post-2026-05-01 review posture (England)",
            jurisdiction="england",
            effective_from="2026-05-01",
            summary_plain=(
                "After 2026-05-01 this ruleset applies a stricter **documentation check** on rent "
                "review clauses: increases must cite the operative clause and notice window that "
                "matches the post-2026 summary policy (heuristic; not a substitute for legal advice)."
            ),
            legal_status_logic=(
                "Post-2026-05-01: require explicit linkage between review clause, index (if any), and "
                "notice date; flag 'naked' increases without clause reference. Statutory rent control "
                "paths remain out of scope for auto-resolution."
            ),
            risk_logic=(
                "HIGH if increase stated without clause reference or notice date after 2026-05-01 "
                "effective window. MEDIUM if index undefined."
            ),
            key_points=[
                "Prefer explicit formula + notice days in contract text.",
                "Manual review if increase predates clause effective date.",
            ],
            red_flags=[
                "Rent uplift with no clause anchor post-2026-05-01.",
                "Conflicting increase dates in the same agreement.",
            ],
            examples=[
                RuleCheckExample(
                    trigger_keywords=["rent increase", "2026-05-01", "clause"],
                    compliant_example="Increase per clause 4 with 60 days' notice after first review date.",
                    risky_example="New rent effective immediately with no clause or notice cited.",
                ),
            ],
            disclaimer_required=True,
        ),
        "access": LegalRule(
            rule_id="access",
            category="landlord_access_and_quiet_enjoyment",
            title="Landlord access and tenant quiet enjoyment (England)",
            jurisdiction="england",
            effective_from="2026-05-01",
            summary_plain=(
                "Quiet enjoyment and reasonable notice for access remain core; emergency carve-outs "
                "unchanged at summary level in this dated version."
            ),
            legal_status_logic=(
                "Same structural tests as current: notice, purpose, emergency exception; post-2026-05-01 "
                "version ID only affects versioning tests, not substantive access text in this stub."
            ),
            risk_logic="HIGH for unannounced entry clauses; MEDIUM for vague notice.",
            key_points=["Notice + purpose", "Emergency narrow"],
            red_flags=["Any time access for non-emergency", "Waiver of quiet enjoyment"],
            examples=[
                RuleCheckExample(
                    trigger_keywords=["access", "notice"],
                    compliant_example="24h notice for inspections except emergency.",
                    risky_example="Landlord entry without notice at landlord convenience.",
                ),
            ],
            disclaimer_required=True,
        ),
        "repairs": LegalRule(
            rule_id="repairs",
            category="repairing_obligations",
            title="Repairing obligations — structure and core services (England)",
            jurisdiction="england",
            effective_from="2026-05-01",
            summary_plain=(
                "Landlord duties for structure, heating, hot water, electrics, and sanitation remain "
                "central; tenant cannot be assigned all statutory landlord repair duties."
            ),
            legal_status_logic=(
                "Allocate repairs consistently; landlord retains core system and structure obligations."
            ),
            risk_logic="HIGH if all repairs on tenant including boiler and roof.",
            key_points=["Structure and core services", "Tenant damage carve-outs"],
            red_flags=["Tenant pays for all repairs including boiler/structure"],
            examples=[
                RuleCheckExample(
                    trigger_keywords=["repairs", "boiler"],
                    compliant_example="Landlord maintains heating and structure.",
                    risky_example="Tenant replaces boiler at sole cost forever.",
                ),
            ],
            disclaimer_required=True,
        ),
        "termination": LegalRule(
            rule_id="termination",
            category="termination_and_break_clauses",
            title="Termination and break clauses — post-2026-05-01 fairness screen (England)",
            jurisdiction="england",
            effective_from="2026-05-01",
            summary_plain=(
                "From 2026-05-01 this ruleset adds an explicit **fairness screen** on break and exit "
                "clauses: asymmetric landlord-only exits without statutory hook are marked for review "
                "(summary-level; courts decide actual enforceability)."
            ),
            legal_status_logic=(
                "Post-2026-05-01: compare landlord vs tenant break rights; flag punitive exit fees vs "
                "stated loss; **detailed forfeiture and possession schedules remain a future module**."
            ),
            risk_logic=(
                "HIGH for one-sided landlord termination + tenant lock-in; MEDIUM for unclear break windows."
            ),
            key_points=[
                "Mutual break preferred signal.",
                "Fees must be proportionate (heuristic).",
            ],
            red_flags=[
                "Landlord immediate termination for convenience; tenant no break.",
                "Opaque termination fees after 2026-05-01 without methodology.",
            ],
            examples=[
                RuleCheckExample(
                    trigger_keywords=["break", "2026-05-01", "termination"],
                    compliant_example="Either party breaks after month 6 with two months' notice.",
                    risky_example="Landlord may end on 7 days; tenant bound for 24 months.",
                ),
            ],
            disclaimer_required=True,
        ),
    }
    return LegalRuleSet(
        ruleset_id="england_post_2026_05_01",
        jurisdiction="england",
        version_label="post_2026_05_01",
        effective_from="2026-05-01",
        rules=rules,
    )
