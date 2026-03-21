# P5 Agent layer — acceptance checklist

Manual checks for **RentalAI** Web UI (`streamlit run app_web.py`). Rule-based Agent only — **no LLM**.

| # | Check | Pass criteria |
|---|--------|----------------|
| 1 | **Natural language input** | **Describe Your Rental Needs** text area accepts mixed EN/中文. |
| 2 | **Parse Request** | Click **Parse Request** → status shows **Parsing** then **Parsed**; structured JSON preview appears. |
| 3 | **RentalIntent** | Preview JSON matches `AgentRentalRequest` fields (`raw_query`, `max_rent`, …). |
| 4 | **Sparse parse** | Vague text still produces preview + info (defaults message); no crash. |
| 5 | **Continue to Analysis** | Syncs **Property details** and runs **analyze-batch** (local or API); status **Submitting** → **Done** or **Error**. |
| 6 | **Batch results reused** | **Batch results** shows criteria, comparison, filters, Top picks, tiers, **View details** (unchanged P4). |
| 7 | **Single /analyze** | **Analyze Property** still runs full dashboard; **Agent summary** appears **after** main sections (below Debug). |
| 8 | **Agent summary** | **Agent summary** block follows results; headline + short text + “What shaped this outcome” bullets; cautions when weak/empty. |
| 9 | **Refine Your Search** | Expander shows when fields missing; quick-action buttons append a line; **Remind me to Parse** shows banner under Agent section. |
| 10 | **Empty batch rows** | `results: []` still shows summary + refine where applicable; not a blank page. |
| 11 | **Batch error** | Transport/API error shows **Error** state + message; Agent summary still renders if `data` missing (N/A — batch block may skip). |
| 12 | **Clear draft** | **Clear draft** resets Agent phase to **Idle**. |
| 13 | **No raw null/undefined** | UI strings use placeholders; no Python `None` leaked as label text. |

## Out of scope (later)

LLM parsing, multi-turn chat, auto re-run after refine, planner, live scraper search, backend redesign.
