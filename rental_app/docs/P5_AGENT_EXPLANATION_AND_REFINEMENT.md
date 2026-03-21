# P5 Phase4 — Agent insights & light refinement

## What shipped

1. **`Agent summary`** panel (`web_ui/agent_summary_panel.py`) **after** main outcomes:
   - **Single `/analyze`**: below the Debug expander (full dashboard first).
   - **Batch**: after filters / Top picks / tier cards (P5 Phase5 order).
2. **Rule-based copy** from `build_agent_insight_bundle` (`web_ui/agent_insight_summary.py`): headline, short summary, bullets (“what drove this view”), cautions (weak scores, sparse intent, few rows).
3. **Missing-field hints** via `get_missing_intent_fields` + `get_refinement_suggestions` (`web_ui/agent_refinement.py`).
4. **Refine your search** expander: suggested questions + **Quick actions** buttons that **append English lines** to **`p5_agent_nl_input`** (scroll up → **Parse request**). **Remind me to Parse** surfaces an info banner in the Agent block.

## Not in this phase

- No LLM / OpenAI  
- No chat transcript or auto re-analysis after refinement  
- No backend or analyze/batch contract changes  
- **P5 Phase5** (separate): Agent layer wrap-up / acceptance

## Intent resolution

`resolve_intent_for_insights` prefers `p5_agent_last_intent`, else first `properties[]` item from the last batch request, else normalized single-analyze form (`AgentRentalRequest.from_normalized_analyze_form` / `from_batch_first_property` in `rental_intent.py`).

## Files

| File | Role |
|------|------|
| `web_ui/agent_refinement.py` | Missing fields + `RefinementSuggestion` |
| `web_ui/agent_insight_summary.py` | `build_agent_insight_bundle`, `resolve_intent_for_insights` |
| `web_ui/agent_summary_panel.py` | `render_agent_insight_panel` |
| `web_ui/rental_intent.py` | Form/batch → approximate `AgentRentalRequest` |
| `app_web.py` | Mounts panels |
| `web_ui/product_copy.py` | English strings |
