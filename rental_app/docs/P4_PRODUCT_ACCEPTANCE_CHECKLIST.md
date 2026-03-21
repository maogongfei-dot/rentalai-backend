# P4 Product acceptance checklist

Light manual checks for the **RentalAI web UI** (`streamlit run app_web.py`).  
Scope: **Product layer only** — single analyze, batch results, cards, filters, details, empty/loading/error states.

## Before you start

1. Optional: start API (`uvicorn api_server:app`) or use **Use local engine** in the sidebar.
2. Open the app; use **Load Demo Data** where helpful.

## Checklist

| # | Item | How to verify |
|---|------|----------------|
| 1 | **Single analyze — result display** | Click **Analyze Property** with valid demo data. Expect: criteria summary, **Overview**, **Listing snapshot** card, score/decision/sections below. No blank result area without a message. |
| 2 | **Single analyze — loading** | While analyze runs, expect a single clear spinner (same wording as defined in product copy). |
| 3 | **Single analyze — validation** | Clear required fields → submit. Expect **Validation** block with errors; app does not crash. |
| 4 | **Single analyze — transport / unexpected error** | With API off and local off, or bad URL: expect **Errors** / status messaging, not a silent blank. |
| 5 | **Batch analyze — list display** | Expand **Batch analysis**, run batch when API available. Expect **Batch results**, criteria snapshot, comparison/risk blocks, then filtered listing area. |
| 6 | **Batch — empty results** | If API returns no `results[]`, expect an **info** empty state (not a blank strip). |
| 7 | **Filter & sort** | With batch rows present: change **Recommendation / Bills / Furnished / Property type / Source / Sort by**. List updates; **no matching listings** shows a **warning** with unified copy. |
| 8 | **Listing card** | Cards show rent, bedrooms, postcode, type, score, summary, badges (**Recommended** / **Not recommended** / **Review needed**). Tier styling differs for **Top pick** vs normal. |
| 9 | **View details** | On analyze and batch cards, expand **View details**. Sections: Overview, Explain, Score, Risks, Source. No raw `undefined`/`None` strings in normal runs. |
| 10 | **Listing link** | **Open listing link** appears only when `source_url` is non-empty (card and detail). |
| 11 | **Top picks** | After batch + filters, **Top picks** (up to 3) and **Results by tier** stay consistent with filtered `displayed` list; no duplicate/conflicting top strip vs tier lists for the same data. |
| 12 | **Result summary** | Batch **Result summary** stats row matches expectations (totals / succeeded / tier counts caption). |
| 13 | **Failed batch row** | If a row has `success: false`, card shows failure styling and message without breaking the page. |
| 14 | **Language consistency** | Primary UI strings are English and aligned with `web_ui/product_copy.py` (e.g. **View details**, **Top picks**, **Result summary**, empty/filter messages). |

## Out of scope (later phases)

Maps, favorites, pagination, scraper UI, new backend endpoints, agent chat, live property search, P5 agent workflow.
