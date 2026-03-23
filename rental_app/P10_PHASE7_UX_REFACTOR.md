# P10 Phase 7 — Product UX refactor (round 1)

## 1. What changed

- **Home input** is now a structured form (property type, bedrooms, bathrooms, optional budget, location, optional distance to centre, optional safety preference) instead of a single text field.
- **Guest mode** for analysis: users without an account (or without a Bearer token) can **start tasks** and **poll results** using a browser-generated `X-Guest-Session` header.
- **Login** is required only for **saving to history** (`POST /records/ui-history`) and **viewing history** (`GET /records/ui-history`); it no longer blocks `POST /tasks` or `GET /tasks/{id}`.
- **Language**: P10 explain copy (`rule_explain.py`) and task-failure explain strings in `api_server.py` are **English**. Static UI copy in `web_public/` is English.
- **UI labels** on the result page align with: Recommendation, Final Score, Property Overview, Explain Summary, Pros, Cons, Risk Flags. The support fold is labelled **Technical details (support)** instead of “raw / debug”.

## 2. Input upgrade

| Field | UI | Backend |
| --- | --- | --- |
| Property type | Select (flat, apartment, house, studio, other, or no preference) | `AnalyzeRealRequest.property_type` → included in `input_summary` and cache signature |
| Bedrooms | Select 1 / 2 / 3 / 4+ or none | `bedrooms` (string) |
| Bathrooms | Minimum bathrooms select | `bathrooms` (float) |
| Budget | Optional £ text | `budget` |
| Postcode / URL | Single location field (URL → `listing_url`, else `target_postcode`) | unchanged scrape behaviour |
| Distance to centre | 1 / 3 / 5 miles or any | `distance_to_centre` — soft filter when listings expose distance |
| Safety | high / medium / low or none | `safety_preference` — **no listing-level safety data**; **high** adds an English risk note after explain is built |

**Adapter (non-scoring)**: `run_multi_source_analysis(..., user_preferences=...)` applies `filter_aggregated_listings_by_preferences` **before** `analyze_multi_source_listings`. If every listing would be filtered out, the pipeline **falls back** to the full aggregated list so the batch does not empty by mistake.

## 3. Guest mode logic

- **Session**: `auth_session.js` stores a UUID in `sessionStorage` and sends **`X-Guest-Session`** on task APIs when there is no Bearer token.
- **Server**: `_get_task_identity()` returns either the real `user_id` from Bearer or `guest:<compact>` derived from the header (or `guest:anonymous` if the header is missing/invalid).
- **Task isolation**: Tasks remain scoped to that identity string, so guests only see their own `task_id` results.
- **Persistence**: `insert_analysis_record` for `multi_source_analysis` uses **`user_id = NULL`** for guest identities so cache rows are not tied to a fake user id; **`find_reusable_analysis_result`** uses the same rule for guests (shared cache by input signature).
- **Copy**: Home and result pages show *“You are not logged in. Your analysis will not be saved.”* when logged out.
- **Nudges**: Clicking **History** while logged out shows *“Login to save your analysis history”* (link blocked). Starting a **second** analysis in the same browser session while logged out shows the same message in an `alert`, then still allows the run. The history page shows the same sentence if opened directly without login.

## 4. Language standard

- **User-facing explain** from `build_p10_explain_*` is English.
- **Web UI** strings in Phase 7–touched files are English (including JS comments in those files).
- **Note**: Other project docs (`README.md`, `P10_PHASE5_DEPLOYMENT.md`, older P10 markdown, comments in `api_server.py`) may still contain Chinese; they were **not** part of this UX pass. The **product surface** (static site + explain JSON fields) is English.

## 5. Limitations

- Guest identity is **per browser** (`sessionStorage`); clearing site data generates a new session and old `task_id` URLs may 404 for the new session.
- **`guest:anonymous`** is shared if no valid header is sent — avoid by always using the provided client script.
- **Safety** and **distance** preferences depend on **scraped fields** being present; missing fields keep listings in the pool (soft behaviour).
- **Password / token** model is unchanged (in-memory tokens, demo-grade security).

## 6. Next step

- Optional **login CTA** on the result page (button next to the guest banner).
- **History** fallback: render from `GET /records/ui-history/{id}` when `GET /tasks/{id}` 404s.
- **i18n** layer if you need a second locale without forking copy.
- Tighten **ops** endpoints (`/tasks/system`, `/records/*`) if they should stay authenticated-only (currently task listing uses the same identity rule as `POST /tasks`).
