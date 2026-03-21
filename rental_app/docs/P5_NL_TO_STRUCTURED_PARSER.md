# P5 Phase2 — Natural language → structured intent (rule parser)

## What this is

- **Rule-based** parser only: **no LLM**, no OpenAI, no extra HTTP.
- Entry function: **`parse_rental_intent(text) -> AgentRentalRequest`** (`web_ui/rental_intent_parser.py`). Product-side name equivalent: **parseRentalIntent**.
- **Phase1** type unchanged: **`AgentRentalRequest`** (`web_ui/rental_intent.py`).

## Supported extraction (best-effort)

| Field | Notes |
|--------|--------|
| `raw_query` | Full original text (trimmed). |
| `max_rent` | `£`, `pcm`, `budget`, `max`, `under`, 中文 `预算` / `不超过` / `以内` / `最多`; bare 4–5 digit only if ≥ 400. |
| `bedrooms` | `N bed`, `one bed`, 中文 `一居`/`两居`/`一室`/`N房`; **studio → 0**. |
| `property_type` | `flat`, `apartment→flat`, `house`, `studio`, `room`; 轻量 `公寓→flat`. |
| `preferred_area` | `in/near/around X`, 中文 `想在…`、`…附近`、`伦敦东边→East London`. |
| `target_postcode` | Full UK-like pattern; `postcode X` / `靠近 X`; outward e.g. `MK9`, `E14`. |
| `bills_included` | `bills included`, `include bills`, `包bill(s)` / `包账单`. |
| `furnished` | `furnished` / `unfurnished`, `带家具` / `不带家具`. |
| `max_commute_minutes` | `within/under N mins`, `N min commute`, `通勤N分钟`, `N分钟以内`. |
| `source_preference` | `rightmove`, `zoopla`. |
| `notes` | Optional cues: pets / parking / garden / gym (not mapped to form). |

Helpers live in the same module: `parse_max_rent`, `parse_bedrooms`, `parse_postcode`, `parse_bills_included`, `parse_furnished`, `parse_commute_minutes`, `parse_preferred_area`, `normalize_property_type`, etc.

## Limitations

- Not linguistic understanding: conflicting numbers, negation, or rare phrasing may mis-parse or miss fields.
- Postcode / area rules are **loose** (no full UK validation).
- **Does not** call **analyze** / **analyze-batch**; **Continue to analysis** only fills the existing Streamlit form (Phase3).

## Frontend

- `web_ui/agent_entry.py` calls **`parse_rental_intent`** on **Parse request**.
- **`intent_has_key_signals`** drives “rich vs sparse” preview copy (`product_copy`).

## Tests

- `python test_rental_intent_parser.py` — includes the four spec examples + edge cases.

## Next: P5 Phase3

Wire **`AgentRentalRequest`** into **Analyze** / **batch** flows (and optional search) without changing core engine contracts in this phase.
