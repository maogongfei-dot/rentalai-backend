# P6 — Scraper local debug flow (Phase1: prep only)

## Current status (Phase1)

- **No** live crawling. **No** Playwright execution in repo yet.  
- Placeholders: `playwright_runner.run_playwright_scrape` returns `[]`; `playwright_available()` is `False`.

## Next phase (when starting real scrape)

1. Add dependency: `playwright` (and run `playwright install chromium` once per machine).  
2. Implement navigation + extraction in **`rightmove_scraper`** first (single list URL, **`max_pages=1`**).  
3. Print or log pipeline stages:
   - **Raw**: HTML snippet or parsed **raw `dict`** per listing (sanitized).  
   - **Normalized**: `ListingSchema` fields after `normalize_listing_batch`.  
   - **Storage**: outcome of storage API only if/when orchestrator writes (keep scraper free of storage if possible).

## Suggested execution path (future)

```text
cd rental_app
# Future: python -m data.scraper.run_dev_job  # Phase2+ CLI 示例
```

Until then, use **`scrape_listings("manual_mock", normalized=True)`** for end-to-end checks without browsers.

## Why “single platform, small scope, few pages”

- Faster feedback on selectors and anti-bot behaviour.  
- Less legal/ethical surface while validating **normalizer + schema** with real-shaped dicts.  
- Easier to diff **raw dict → ListingSchema** before scaling volume.

## Outputs worth saving during debug (Phase2+)

| Output | Purpose |
|--------|---------|
| Trimmed HTML | Regress selector changes offline |
| Raw `list[dict]` | Unit tests for normalizer |
| `ListingSchema` JSON | Confirm mapping before storage |

Store under `data/scraper/samples/` only **redacted** data; do not commit secrets or PII.
