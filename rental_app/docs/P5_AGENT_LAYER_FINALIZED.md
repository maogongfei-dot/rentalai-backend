# P5 Agent layer — finalized (Phase1–5)

## Completed (MVP)

| Phase | Delivered |
|-------|-----------|
| **1** | **Describe Your Rental Needs** entry, NL text, Parse, structured preview, session flow. |
| **2** | Rule-based **`parse_rental_intent`** → **`AgentRentalRequest`** (EN/中文/混合). |
| **3** | **`Continue to Analysis`** → **`analyze-batch`** (one `properties[]` row); local **`analyze_batch_request_body`** or HTTP; reuses **`p2_batch_last`**. |
| **4** | **`build_agent_insight_bundle`** + **Refine Your Search** (append NL snippets). |
| **5** | Unified **phase names** (`idle`, `parsing`, `parsed`, `submitting`, `analysis_success`, `analysis_error`), **product_copy**文案收口, **Agent summary** moved **after** single/batch results, legacy session migration. |

## What the Agent layer can do today

- One-shot NL → structured preview → form sync → batch analysis → existing P4 cards/filters/details.  
- Rule-based **Agent summary** and **refinement** prompts after results.  
- Stable demo without OpenAI or new backend contracts.

## Not included (by design)

- LLM / embeddings / tool-calling  
- Multi-turn conversational UI or auto re-analysis after refine  
- Agent planner or goal decomposition  
- Automatic real-listing search (scraper-driven)  
- New scoring engines or API shapes  

## Positioning

Suitable as a **demo-ready Agent MVP**: guided input, transparent defaults, and reuse of the existing analysis UI.

## Likely next upgrades

- LLM slot-in behind `parse_rental_intent`  
- Optional second turn (“clarify budget only”) without full chat  
- Deeper links from Refine actions to form fields  
- Planner + search once data/scraper product phases allow  

See **`docs/P5_AGENT_ACCEPTANCE_CHECKLIST.md`** for manual verification.
