# P6 — Playwright integration plan (Phase1: planning only)

## Why Playwright

Rental portals (Rightmove / Zoopla) rely heavily on client-rendered HTML and bot mitigation. **Playwright** gives a real browser context (JS execution, cookies, viewport), which is more reliable than raw `requests` for listing pages. It fits **after** the existing pipeline: scrapers still return **`list[dict]`**, then **normalizer** → **`ListingSchema`** → **storage** (unchanged contracts).

## Platform order

1. **Rightmove first** — larger rental inventory in target market, URL/search patterns slightly more stable for an initial vertical slice; single-platform loop reduces moving parts.  
2. **Zoopla second** — same architecture (`BaseListingScraper` + selectors + runner); reuse patterns from Rightmove.  
3. **`manual_mock`** — keep for unit tests and offline dev **without** Playwright.

## Code layout (under `data/scraper/`)

| Piece | Role |
|--------|------|
| `scraper_config.py` | `ScraperRunConfig` — URL, pages, limits, headless, debug flags |
| `playwright_runner.py` | Future browser lifecycle + navigation (Phase1: stub) |
| `rightmove_scraper.py` / `zoopla_scraper.py` | Platform classes; Phase2+ may call runner internally |
| `selectors/` | Selector notes / constants (Phase2+); no real selectors in Phase1 |
| `samples/` | Sanitized HTML/JSON fixtures for local parsing tests |

## Planned end-to-end chain

```
ScraperRunConfig (search_url, max_pages, limit, …)
    → playwright_runner.run_playwright_scrape (Phase2+)
    → platform-specific extraction → list[dict] (raw listings)
    → scrape_listings(..., normalized=True) or normalize_listing_batch(raw, source)
    → list[ListingSchema]
    → storage (caller/orchestrator; not inside scraper package core)
```

`listing_scraper.scrape_listings` remains the **public dispatch**; wiring config → runner can live in a thin CLI or future job module (Phase2+).

## Local debugging (summary)

- Install Playwright browsers **only when starting Phase2** (`playwright install`).  
- Start with **one platform, one search URL, `max_pages=1`, small `limit`**.  
- Optional: `headless=False`, `save_raw_html` / `save_screenshots` on a dedicated output dir (implement in Phase2).  

Details: **`docs/P6_SCRAPER_LOCAL_DEBUG_FLOW.md`**.

## This phase (Phase1)

- **No** real scraping, **no** Playwright install in CI/requirements unless explicitly added later.  
- **No** changes to **schema / normalizer / storage** core logic.  
- Deliverables: **structure**, **`ScraperRunConfig`**, **runner stub**, **docs**.
