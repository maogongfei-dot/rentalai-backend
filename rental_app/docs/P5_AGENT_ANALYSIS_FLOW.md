# P5 Phase3 — Agent → analyze / analyze-batch wiring

## What shipped

1. **Intent → API payload** (`web_ui/intent_to_payload.py`): `build_batch_property_from_intent`, `build_batch_request_from_intent`, `build_analyze_raw_form_from_intent`, `merge_intent_metadata_for_area`.
2. **Scheduler** (`web_ui/agent_runner.py`): **`run_agent_intent_analysis`** — always **`POST /analyze-batch`** with **`properties: [ one item ]`** (single “search scenario”).
3. **Agent UI** (`web_ui/agent_entry.py`): **Continue to analysis** fills the **Property details** form from the same numbers as the batch row, then runs the batch (spinner). **Local engine** mode calls **`analyze_batch_request_body`** in-process (no HTTP); API mode uses **`requests.post(.../analyze-batch)`**.
4. **Results**: Reuses existing **`p2_batch_last` / `p2_batch_last_request`** and the same **Batch results** block (stats, Top picks, tiers, filters, **View details**).

## Dispatch rule (Phase3)

| Path | When |
|------|------|
| **analyze-batch** | Default for Agent NL flow (one synthetic property from intent). |
| **Single /analyze** | Not auto-triggered by Agent; user can still use **Analyze Property** with the synced form. |

`property_type`, `furnished`, `source_preference`, extra `notes` are **not** separate API fields: they are merged into **`area`** as text (source is explicitly marked “not used by engine”).

## Agent session phases (UI)

`idle` → `parsing_preview` → `parsed_result` → **`submitting`** → **`analysis_success`** | **`analysis_error`**.

## P5 Phase4 (related)

Rule-based **Agent insights** + **Refine your search** (append NL snippets) sit above single/batch results — see **`docs/P5_AGENT_EXPLANATION_AND_REFINEMENT.md`**.

## Limitations (by design)

- **No LLM**, no multi-turn chat, no planner, no scraper.
- Sparse parses still run batch using **numeric defaults** (same spirit as `web_bridge` defaults).
- **P5 Phase4** (separate): richer explanations, optional follow-up prompts.

## Files

| File | Role |
|------|------|
| `web_ui/intent_to_payload.py` | RentalIntent → batch / form |
| `web_ui/agent_runner.py` | `run_agent_intent_analysis` |
| `web_ui/agent_entry.py` | Parse, Continue, state, spinner |
| `docs/P5_AGENT_ANALYSIS_FLOW.md` | This note |
