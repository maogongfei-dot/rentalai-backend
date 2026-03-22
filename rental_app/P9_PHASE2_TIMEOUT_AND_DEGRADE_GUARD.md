# P9 Phase2 Timeout and Degrade Guard

## 1. Guard Scope

**Protected this round:**

| Module | Guard type |
|--------|-----------|
| `multi_source_pipeline` | Per-source timeout (`RENTALAI_SOURCE_TIMEOUT`, default 120 s) |
| `real_analysis_service` | Overall hard timeout (`RENTALAI_REAL_ANALYSIS_TIMEOUT`, default 180 s) |
| `analysis_bridge` | Degraded-mode flag when pipeline partially fails |
| `app_web` local engine path | Slow-engine warning + structured error message |

**Not touched this round:**

- Scraper internals (Playwright browser-level timeouts remain at their existing 45 s selector wait).
- Individual `run_rightmove_pipeline` / `run_zoopla_pipeline` function bodies — they already have `try/except` around scraper calls.
- FastAPI request-level timeouts — the existing middleware slow-request alert (5 s threshold) covers observation; Render/Gunicorn workers provide the hard server timeout.

## 2. Frontend Guards

### 2a. `app_web.py` — local engine path

- Added slow-engine detection: if the local analysis engine takes longer than 10 s, a `[PERF][SLOW]` warning is logged.
- Changed the generic `except Exception` return to include structured error context (`"Analysis engine error: ..."`) rather than a bare `str(e)`.
- Existing HTTP-mode timeouts are already in place (`timeout=120` for single analyze, `timeout=180` for batch).

### 2b. `real_analysis_service.py` — overall hard timeout

- `run_real_listings_analysis` now runs `run_multi_source_analysis` inside a `ThreadPoolExecutor` with a configurable hard timeout (default 180 s via `RENTALAI_REAL_ANALYSIS_TIMEOUT`).
- On timeout, the function returns a synthetic failure envelope with a clear user-facing message ("...timed out after Ns. Try fewer sources or a smaller limit.") and logs a `[TIMEOUT]` error.
- This prevents a hung scraper or analysis from blocking the Streamlit UI indefinitely.

## 3. Backend Guards

### 3a. `multi_source_pipeline.py` — per-source timeout

- Each source pipeline (`run_rightmove_pipeline`, `run_zoopla_pipeline`) now has a `concurrent.futures` result timeout of `RENTALAI_SOURCE_TIMEOUT` seconds (default 120).
- If a single source exceeds the timeout, a structured timeout result is synthesized (`success: false, error: "timeout after Ns"`) and logged with `[PERF][TIMEOUT]`.
- The remaining sources' results are still collected — one source hanging does not block the others.

### 3b. Existing guards (unchanged, verified adequate)

- FastAPI global exception handler already catches all 500s, logs traceback, and triggers a P1 alert.
- HTTP middleware already flags slow requests (> 5 s) with `[PERF][SLOW]` and a P2 alert.
- `analysis_bridge.run_multi_source_analysis` already has early validation (`limit_per_source > 0`).
- `/analyze-batch` already has a max-items cap (`RENTALAI_BATCH_MAX`, default 50).

## 4. Scraper / Analysis Guards

### 4a. `analysis_bridge.py` — degraded-mode flag

- The output dict now includes a `degraded` boolean field.
- When the analysis engine succeeds but the pipeline reports partial failure (e.g. one source timed out), `degraded` is set to `True` and a `[DEGRADED]` warning is logged.
- Downstream consumers (UI, API) can use this flag to display a "partial results" indicator.

### 4b. Scraper-level protection (existing)

- Playwright selector waits already use `timeout=45_000` (45 s) — card detection won't hang forever.
- `_fetch_rightmove_page` wraps the entire browser session in `try/except` and returns `(0, [])` on failure.
- Per-source pipeline timeout (120 s) is a second safety net above the browser-level timeout.

## 5. Degrade Strategy

| Module failure | System behavior |
|----------------|----------------|
| One scraper source times out / errors | Other sources continue; analysis runs on collected listings; `degraded=True` |
| All scraper sources fail | Analysis bridge returns `success=False` with error details; UI shows "No listings found" |
| Analysis engine fails | Envelope contains error; UI shows message; no crash |
| `run_real_listings_analysis` times out | Synthetic failure envelope returned; UI shows timeout message |
| Local engine slow (> 10 s) | Warning logged; result still returned normally |
| Backend API 500 | Global handler returns structured JSON; P1 alert fired |

**MVP degradation boundary:** The system never crashes or hangs indefinitely. Partial failures are surfaced as structured results. Only a full infrastructure failure (Render down, Streamlit process killed) falls outside current protection.

## 6. Risk Control Notes

- **No business logic changed.** All guards are around call boundaries (timeouts, try/except, flag additions). Analysis scoring, API return structures, and UI rendering logic are untouched.
- **`degraded` field is additive.** It's a new key in the bridge output dict. Existing consumers that don't read it are unaffected.
- **Thread timeout is cooperative.** Python `concurrent.futures` timeouts release the caller but the worker thread may continue running until the underlying I/O completes. This is acceptable for MVP — it prevents the caller from waiting, even though the background thread leaks temporarily.
- **Existing Playwright timeouts remain as-is.** They already provide 45 s limits on selector waits, which is reasonable for a single page load.

## 7. Remaining Stability Risks

1. **GIL + CPU-bound analysis:** `ThreadPoolExecutor` timeout releases the caller, but the worker still holds GIL for CPU-bound analysis. Under extreme load this could degrade overall process performance.
2. **Render cold start:** First request after idle may combine Playwright install + browser launch + analysis. The 120 s per-source timeout should accommodate this, but Render's free tier has a 15-minute spin-down.
3. **No circuit breaker:** If a source consistently times out, the system still tries it every request. A circuit-breaker pattern (skip source for N minutes after K failures) would be a future improvement.
4. **No request-level cancellation in FastAPI:** If a client disconnects mid-request, the backend continues processing. Starlette's `disconnect` event could be wired up in the future.
5. **Storage I/O on failure path:** Even when degraded, the pipeline may attempt file writes (debug samples, listings.json). On read-only file systems this silently fails (already guarded by `try/except` in storage code).

## 8. Next Priorities

1. **Circuit breaker for flaky sources** — skip a source for a cooldown period after consecutive timeouts.
2. **Request cancellation** — propagate client disconnect to cancel in-flight scraper/analysis work.
3. **Memory-level metrics endpoint** — expose request counts, timeout counts, and average durations via `/metrics` for operational visibility.
