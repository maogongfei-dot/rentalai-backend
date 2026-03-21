# P5 Phase1 — AI Agent entry & rental intent shell

## What shipped

1. **Agent entry** on the main Streamlit page (`app_web.py`), **above** **Property details**.
2. **Structured target type** `AgentRentalRequest` in `web_ui/rental_intent.py` (P5 natural-language → structured goal; aligns with existing analyze form fields where applicable).
3. **Rule parser** `parse_rental_intent` in `web_ui/rental_intent_parser.py` (Phase2). `parse_rental_intent_mock` remains an alias in `agent_intent_mock_parser.py`.
4. **UI flow** in `web_ui/agent_entry.py`: states `idle` → `parsing_preview` → `parsed_result` → `ready_for_analysis` (session keys `p5_agent_*`).
5. **Continue to analysis** (Phase3) syncs the form and runs **analyze-batch** (one property); results reuse **Batch results** below. **Analyze Property** remains available for single `/analyze`.

## Not in scope (later phases)

| Phase | Planned work |
|-------|----------------|
| **Phase2** | **Done (rules):** `parse_rental_intent` + helpers — still no LLM. |
| **Phase3** | **Done:** Agent **Continue** → **analyze-batch** (`intent_to_payload` + `agent_runner`). Optional **Analyze** still manual. |
| **Phase4+** | Follow-ups, richer explanations, search/scraper, planner (out of scope). |

## Current limitations

- **No** OpenAI / LLM / HTTP parse API.
- **No** multi-turn chat or follow-up questions.
- **No** change to analyze or analyze-batch **request contracts**; only optional **form pre-fill** from the mock preview.

## Files

| File | Role |
|------|------|
| `web_ui/rental_intent.py` | `AgentRentalRequest` dataclass + `to_dict` / `from_dict` |
| `web_ui/rental_intent_parser.py` | `parse_rental_intent`, `intent_has_key_signals` |
| `web_ui/agent_intent_mock_parser.py` | Alias `parse_rental_intent_mock` → `parse_rental_intent` |
| `web_ui/agent_entry.py` | Streamlit section + state + form sync |
| `web_ui/product_copy.py` | English strings for the Agent block |
| `docs/P5_AGENT_ENTRY_FLOW.md` | This note |
