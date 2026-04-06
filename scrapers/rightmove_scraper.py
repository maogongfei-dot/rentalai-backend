"""
Phase 2: Rightmove single-listing parser (requests + BeautifulSoup).

Public entry for batch / future list pipelines: scrape_rightmove_listing(url).
Search results → detail URLs: extract_rightmove_listing_links(search_url);
multi-page links: extract_rightmove_listing_links_from_pages(search_url, pages).
Batch: scrape_rightmove_search_results(search_url, limit);
multi-page batch: scrape_rightmove_search_results_from_pages(search_url, pages, limit).
Batch clean/summary: clean_rightmove_results, summarize_rightmove_results.
Batch export: export_rightmove_results(search_url, results).
Multi-page export/save: export_rightmove_results_from_pages, save_rightmove_results_from_pages.
Multi-page JSON load/validate: load_rightmove_results_from_pages_json, validate_rightmove_export_data.
Unified service entry: run_rightmove_service(mode, url, ...).
Payload entry: run_rightmove_service_from_payload(payload).
Pipeline entry: execute_rightmove_pipeline(payload).
API-style wrapper: build_rightmove_response(ok, mode, data, error, meta); merge_rightmove_meta for meta.
Save to JSON: save_rightmove_export_to_json(export_data, file_path).
Core HTML/JSON parsing: parse_rightmove_listing(url).

Standalone — not wired to chat/router. Extend later for multi-page / Playwright.

Defaults (timeouts, limits, headers, ``SUMMARY_CORE_FIELDS``) live in the Config Block after imports.

Input validation helpers: ``validate_rightmove_mode``, ``validate_rightmove_url_input``,
``normalize_limit_input``, ``normalize_pages_input``, ``validate_output_file_input``,
``validate_rightmove_payload_input``.

Mode registry: ``RIGHTMOVE_MODE_REGISTRY``, ``get_supported_rightmove_modes``,
``get_rightmove_mode_description``.

Task descriptor: ``build_rightmove_task_descriptor``, ``get_rightmove_task_descriptor_by_mode``.

Example payloads: ``build_rightmove_example_payloads``, ``get_rightmove_example_payload_by_mode``.

Self check: ``build_rightmove_self_check_report``, ``run_rightmove_self_check``.

Capability map: ``build_rightmove_capability_map``, ``get_rightmove_capability_status``.

Module snapshot: ``build_rightmove_module_snapshot``, ``get_rightmove_snapshot_section``.

Module manifest: ``build_rightmove_module_manifest``, ``get_rightmove_manifest_entry``.

Service result summary: ``build_rightmove_result_summary``, ``build_rightmove_response_with_summary``.

Phase 2 finalization: ``build_rightmove_module_status``, ``is_rightmove_module_ready``.

Dependencies: pip install requests beautifulsoup4
"""

# ================================
# RentalAI - Phase 2 Completed
# Rightmove Scraper Module (v1)
# ================================

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup, Tag

# --- Rightmove scraper defaults (Config Block v1) ---
RIGHTMOVE_PLATFORM = "rightmove"
DEFAULT_LIMIT = 10
DEFAULT_PAGES = 1
DEFAULT_BATCH_LIMIT = 5
DEFAULT_TIMEOUT = 15
DEFAULT_OUTPUT_FILE = "rightmove_export_test.json"

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-GB,en;q=0.9",
}

SUMMARY_CORE_FIELDS = [
    "total_results",
    "valid_results",
    "success_count",
    "partial_count",
    "error_count",
]

RIGHTMOVE_MODE_REGISTRY: dict[str, str] = {
    "single": "single listing scrape",
    "search_links": "extract listing links from one search page",
    "batch": "batch scrape from one search page",
    "multi_page_batch": "batch scrape from multiple search pages",
    "export": "export multi-page batch results",
    "save": "export and save multi-page batch results to json",
}

# Per-mode flags: requires_url, supports_limit, supports_pages, supports_output_file (keys == registry)
_RIGHTMOVE_MODE_TASK_CAPS: dict[str, tuple[bool, bool, bool, bool]] = {
    "single": (True, False, False, False),
    "search_links": (True, False, False, False),
    "batch": (True, True, False, False),
    "multi_page_batch": (True, True, True, False),
    "export": (True, True, True, False),
    "save": (True, True, True, True),
}
assert set(_RIGHTMOVE_MODE_TASK_CAPS.keys()) == set(RIGHTMOVE_MODE_REGISTRY.keys())

_BED_RE = re.compile(
    r"(\d+)\s*(?:bed(?:room)?s?|br\b)",
    re.I,
)
_BATH_RE = re.compile(
    r"(\d+)\s*bath(?:room)?s?",
    re.I,
)
_PRICE_PCM_RE = re.compile(
    r"£\s*([\d,]+(?:\.\d+)?)\s*(?:pcm|p\.c\.m\.|per\s*month|/month|a\s*month)?",
    re.I,
)
_PRICE_ANY_RE = re.compile(r"£\s*([\d,]+(?:\.\d+)?)")
_PROPERTY_TYPE_RE = re.compile(
    r"\b(flat|apartment|house|bungalow|studio|maisonette|cottage|penthouse|detached|terraced)\b",
    re.I,
)

# Regex hints on raw HTML (embedded JSON fragments)
_HTML_PRICE_HINTS = (
    re.compile(r'"price":\s*"?(\d+)"?', re.I),
    re.compile(r'"pricePerMonth":\s*(\d+)', re.I),
    re.compile(r'"rent":\s*(\d+)', re.I),
    re.compile(r'"amount":\s*(\d+)', re.I),
    re.compile(r'"formattedPrice":\s*"£([\d,]+)', re.I),
)
_HTML_BED_HINTS = (
    re.compile(r'"bedrooms":\s*(\d+)', re.I),
    re.compile(r'"beds":\s*(\d+)', re.I),
    re.compile(r'"numberOfBedrooms":\s*(\d+)', re.I),
)
_HTML_BATH_HINTS = (
    re.compile(r'"bathrooms":\s*(\d+)', re.I),
    re.compile(r'"numberOfBathrooms":\s*(\d+)', re.I),
)
_MEDIA_IMG_RE = re.compile(
    r"https://media\.rightmove\.co\.uk/[^\s\"'<>]+",
    re.I,
)


def build_empty_result(url: str) -> dict[str, Any]:
    """Fixed-shape payload for parse_rightmove_listing (defaults + status shell)."""
    u = (url or "").strip()
    return {
        "platform": RIGHTMOVE_PLATFORM,
        "url": u,
        "price": None,
        "address": None,
        "bedrooms": None,
        "bathrooms": None,
        "property_type": None,
        "description": None,
        "images": [],
        "raw_text": "",
        "status": "partial",
        "error": None,
    }


def build_empty_rightmove_export(search_url: str = "") -> dict[str, Any]:
    """Fixed-shape empty export payload (matches export_rightmove_results when empty)."""
    su = (search_url or "").strip() if isinstance(search_url, str) else str(search_url or "").strip()
    return {
        "platform": RIGHTMOVE_PLATFORM,
        "search_url": su,
        "results": [],
        "cleaned_results": [],
        "summary": {
            "total_results": 0,
            "valid_results": 0,
            "success_count": 0,
            "partial_count": 0,
            "error_count": 0,
            "with_price_count": 0,
            "with_address_count": 0,
            "with_description_count": 0,
            "avg_price": None,
            "min_price": None,
            "max_price": None,
        },
    }


def build_rightmove_response(
    ok: bool,
    mode: str | None,
    data: Any = None,
    error: str | None = None,
    meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Standard envelope for service/payload results (no business logic).

    Merges ``meta`` with default platform; ``platform`` is always ``RIGHTMOVE_PLATFORM``.
    """
    merged: dict[str, Any] = {"platform": RIGHTMOVE_PLATFORM}
    if meta and isinstance(meta, dict):
        merged.update(meta)
    merged["platform"] = RIGHTMOVE_PLATFORM
    return {
        "ok": ok,
        "mode": mode,
        "data": data,
        "error": error,
        "meta": merged,
    }


def detect_rightmove_data_type(data: Any) -> str | None:
    """Return a simple type label for ``data`` (``dict`` / ``list`` / ``str`` / ``None`` / ``__name__``)."""
    if data is None:
        return None
    if isinstance(data, dict):
        return "dict"
    if isinstance(data, list):
        return "list"
    if isinstance(data, str):
        return "str"
    return type(data).__name__


def _rightmove_data_has_content(data: Any) -> bool:
    """True if ``data`` is present and not an empty list/dict/str."""
    if data is None:
        return False
    if isinstance(data, (list, dict)):
        return len(data) > 0
    if isinstance(data, str):
        return bool(data.strip())
    return True


def build_rightmove_result_summary(response: dict[str, Any]) -> dict[str, Any]:
    """
    Derive a lightweight summary from a unified service/payload/pipeline response dict.

    Never raises; invalid ``response`` yields a default-shaped summary.
    """
    empty = {
        "ok": False,
        "mode": None,
        "platform": RIGHTMOVE_PLATFORM,
        "has_data": False,
        "data_type": None,
        "item_count": 0,
        "error": None,
    }
    if not isinstance(response, dict):
        return dict(empty)

    ok = response.get("ok")
    if not isinstance(ok, bool):
        ok = False

    mode = response.get("mode")
    meta = response.get("meta")
    platform = RIGHTMOVE_PLATFORM
    if isinstance(meta, dict):
        mp = meta.get("platform")
        if isinstance(mp, str) and mp.strip():
            platform = mp.strip()

    data = response.get("data")
    data_type = detect_rightmove_data_type(data)
    has_data = _rightmove_data_has_content(data)

    item_count = 0
    if isinstance(data, list):
        item_count = len(data)
    elif isinstance(data, dict):
        cr = data.get("cleaned_results")
        if isinstance(cr, list):
            item_count = len(cr)
        else:
            item_count = 1

    err = response.get("error")
    if err is not None and not isinstance(err, str):
        err = str(err)

    return {
        "ok": ok,
        "mode": mode,
        "platform": platform,
        "has_data": has_data,
        "data_type": data_type,
        "item_count": item_count,
        "error": err,
    }


def build_rightmove_response_with_summary(response: Any) -> dict[str, Any]:
    """
    Return a shallow copy of ``response`` with an added ``summary`` key.

    If ``response`` is not a dict, returns a safe minimal envelope (never raises).
    """
    if not isinstance(response, dict):
        return {
            "ok": False,
            "mode": None,
            "data": None,
            "error": "invalid response",
            "meta": {"platform": RIGHTMOVE_PLATFORM},
            "summary": build_rightmove_result_summary({}),
        }
    out = dict(response)
    out["summary"] = build_rightmove_result_summary(response)
    return out


def _normalize_service_mode(mode: Any) -> str:
    if isinstance(mode, str):
        return mode.strip()
    if mode is None:
        return ""
    return str(mode).strip()


def validate_rightmove_mode(mode: str | None) -> tuple[bool, str | None]:
    """Return (True, None) if ``mode`` is a supported service mode; else (False, ``unsupported mode``)."""
    m = _normalize_service_mode(mode)
    if not m or m not in RIGHTMOVE_MODE_REGISTRY:
        return False, "unsupported mode"
    return True, None


def validate_rightmove_url_input(url: str | None) -> tuple[bool, str | None]:
    """Return (True, None) if ``url`` is non-empty after strip; else (False, ``empty url``)."""
    u = (url or "").strip() if isinstance(url, str) else str(url or "").strip()
    if not u:
        return False, "empty url"
    return True, None


def normalize_limit_input(limit: int | None) -> int:
    """Positive int limit, or ``DEFAULT_LIMIT`` if missing/invalid/non-positive."""
    try:
        n = int(limit)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return DEFAULT_LIMIT
    if n <= 0:
        return DEFAULT_LIMIT
    return n


def normalize_pages_input(pages: int | None) -> int:
    """Positive int pages, or ``DEFAULT_PAGES`` if missing/invalid/non-positive."""
    try:
        n = int(pages)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return DEFAULT_PAGES
    if n <= 0:
        return DEFAULT_PAGES
    return n


def validate_output_file_input(output_file: str | None) -> tuple[bool, str | None]:
    """Non-empty stripped path for save mode; else (False, ``empty output_file``)."""
    of = ""
    if isinstance(output_file, str):
        of = output_file.strip()
    elif output_file is not None:
        of = str(output_file).strip()
    if not of:
        return False, "empty output_file"
    return True, None


def validate_rightmove_payload_input(payload: dict | None) -> tuple[bool, str | None]:
    """Return (False, ``invalid payload``) if ``payload`` is not a dict."""
    if not isinstance(payload, dict):
        return False, "invalid payload"
    return True, None


def get_supported_rightmove_modes() -> list[str]:
    """Return supported service mode names (keys of ``RIGHTMOVE_MODE_REGISTRY``)."""
    return list(RIGHTMOVE_MODE_REGISTRY.keys())


def get_rightmove_mode_description(mode: str | None) -> str | None:
    """Return the registry description for ``mode``, or None if unknown."""
    m = _normalize_service_mode(mode)
    if not m:
        return None
    return RIGHTMOVE_MODE_REGISTRY.get(m)


def build_rightmove_task_descriptor() -> dict[str, Any]:
    """Lightweight module task/capability table for router/chat/API consumers."""
    return {
        "platform": RIGHTMOVE_PLATFORM,
        "module": "scraper",
        "supported_modes": get_supported_rightmove_modes(),
        "mode_descriptions": dict(RIGHTMOVE_MODE_REGISTRY),
        "default_limit": DEFAULT_LIMIT,
        "default_pages": DEFAULT_PAGES,
        "supports_export": True,
        "supports_save": True,
        "supports_load": True,
    }


def get_rightmove_task_descriptor_by_mode(mode: str | None) -> dict[str, Any]:
    """
    Per-mode parameter hints. Unknown modes return ``supported: False`` (never raises).
    """
    m = _normalize_service_mode(mode)
    unsupported = {
        "mode": m if m else None,
        "supported": False,
        "description": None,
        "requires_url": True,
        "supports_limit": False,
        "supports_pages": False,
        "supports_output_file": False,
    }
    if not m or m not in RIGHTMOVE_MODE_REGISTRY:
        return unsupported
    ru, sl, sp, so = _RIGHTMOVE_MODE_TASK_CAPS[m]
    return {
        "mode": m,
        "supported": True,
        "description": RIGHTMOVE_MODE_REGISTRY.get(m),
        "requires_url": ru,
        "supports_limit": sl,
        "supports_pages": sp,
        "supports_output_file": so,
    }


def build_rightmove_example_payloads(
    test_url: str,
    search_url: str,
    output_file: str = DEFAULT_OUTPUT_FILE,
) -> dict[str, Any]:
    """
    Build example request payloads for each supported mode (keys from ``RIGHTMOVE_MODE_REGISTRY``).

    No network I/O; for docs/router/chat only.
    """
    out: dict[str, Any] = {}
    for m in get_supported_rightmove_modes():
        if m == "single":
            out[m] = {"mode": "single", "url": test_url}
        elif m == "search_links":
            out[m] = {"mode": "search_links", "url": search_url}
        elif m == "batch":
            out[m] = {"mode": "batch", "url": search_url, "limit": DEFAULT_BATCH_LIMIT}
        elif m == "multi_page_batch":
            out[m] = {
                "mode": "multi_page_batch",
                "url": search_url,
                "pages": DEFAULT_PAGES,
                "limit": DEFAULT_BATCH_LIMIT,
            }
        elif m == "export":
            out[m] = {
                "mode": "export",
                "url": search_url,
                "pages": DEFAULT_PAGES,
                "limit": DEFAULT_BATCH_LIMIT,
            }
        elif m == "save":
            out[m] = {
                "mode": "save",
                "url": search_url,
                "pages": DEFAULT_PAGES,
                "limit": DEFAULT_BATCH_LIMIT,
                "output_file": output_file,
            }
    return out


def get_rightmove_example_payload_by_mode(
    mode: str | None,
    test_url: str,
    search_url: str,
    output_file: str = DEFAULT_OUTPUT_FILE,
) -> dict[str, Any]:
    """
    Return one example payload envelope for ``mode``. Unknown modes get ``supported: False`` (never raises).
    """
    m = _normalize_service_mode(mode)
    if not m or m not in RIGHTMOVE_MODE_REGISTRY:
        return {
            "mode": m if m else None,
            "supported": False,
            "payload": None,
            "error": "unsupported mode",
        }
    table = build_rightmove_example_payloads(test_url, search_url, output_file)
    return {
        "mode": m,
        "supported": True,
        "payload": table.get(m),
        "error": None,
    }


def _self_check_callable(name: str) -> bool:
    g = globals()
    return name in g and callable(g[name])


def _self_check_callables(names: tuple[str, ...]) -> bool:
    return all(_self_check_callable(n) for n in names)


def _self_check_config_ok() -> bool:
    try:
        if not RIGHTMOVE_PLATFORM:
            return False
        if DEFAULT_LIMIT is None or DEFAULT_PAGES is None:
            return False
        if not isinstance(DEFAULT_HEADERS, dict) or not DEFAULT_HEADERS:
            return False
        if not isinstance(RIGHTMOVE_MODE_REGISTRY, dict) or not RIGHTMOVE_MODE_REGISTRY:
            return False
        return True
    except Exception:
        return False


def build_rightmove_self_check_report() -> dict[str, Any]:
    """
    Lightweight presence check for config and public entrypoints (no network I/O).

    Call after module load; uses ``globals()`` name lookup only.
    """
    checks: dict[str, bool] = {
        "config_ok": _self_check_config_ok(),
        "mode_registry_ok": _self_check_callables(
            ("get_supported_rightmove_modes", "get_rightmove_mode_description")
        ),
        "task_descriptor_ok": _self_check_callables(
            ("build_rightmove_task_descriptor", "get_rightmove_task_descriptor_by_mode")
        ),
        "example_payloads_ok": _self_check_callables(
            ("build_rightmove_example_payloads", "get_rightmove_example_payload_by_mode")
        ),
        "single_scrape_ok": _self_check_callables(("parse_rightmove_listing", "scrape_rightmove_listing")),
        "search_links_ok": _self_check_callables(("extract_rightmove_listing_links",)),
        "batch_ok": _self_check_callables(("scrape_rightmove_search_results",)),
        "multi_page_batch_ok": _self_check_callables(
            ("extract_rightmove_listing_links_from_pages", "scrape_rightmove_search_results_from_pages")
        ),
        "export_ok": _self_check_callables(("export_rightmove_results", "export_rightmove_results_from_pages")),
        "save_ok": _self_check_callables(("save_rightmove_export_to_json", "save_rightmove_results_from_pages")),
        "load_ok": _self_check_callables(("load_rightmove_export_from_json", "load_rightmove_results_from_pages_json")),
        "service_ok": _self_check_callables(("run_rightmove_service",)),
        "payload_ok": _self_check_callables(("run_rightmove_service_from_payload",)),
        "pipeline_ok": _self_check_callables(("execute_rightmove_pipeline",)),
        "response_wrapper_ok": _self_check_callables(
            ("build_rightmove_response", "build_rightmove_response_with_summary")
        ),
        "summary_ok": _self_check_callables(("build_rightmove_result_summary",)),
    }
    missing = [k for k, v in checks.items() if not v]
    return {
        "platform": RIGHTMOVE_PLATFORM,
        "module": "scraper",
        "ok": len(missing) == 0,
        "checks": checks,
        "missing": missing,
    }


def run_rightmove_self_check() -> None:
    """Print JSON self-check report to stdout."""
    r = build_rightmove_self_check_report()
    print(json.dumps(r, ensure_ascii=False, indent=2))


RIGHTMOVE_CAPABILITY_KEYS: tuple[str, ...] = (
    "single_listing_parse",
    "search_links_extract",
    "batch_scrape_single_page",
    "batch_scrape_multi_page",
    "export_results",
    "save_results",
    "load_results",
    "service_entry",
    "payload_entry",
    "pipeline_entry",
    "response_wrapper",
    "result_summary",
    "task_descriptor",
    "example_payloads",
    "self_check",
)


def _build_rightmove_capabilities_from_self_check() -> dict[str, bool]:
    """Map self-check flags to stable capability keys (no network I/O)."""
    ch = build_rightmove_self_check_report()["checks"]
    return {
        "single_listing_parse": ch["single_scrape_ok"],
        "search_links_extract": ch["search_links_ok"],
        "batch_scrape_single_page": ch["batch_ok"],
        "batch_scrape_multi_page": ch["multi_page_batch_ok"],
        "export_results": ch["export_ok"],
        "save_results": ch["save_ok"],
        "load_results": ch["load_ok"],
        "service_entry": ch["service_ok"],
        "payload_entry": ch["payload_ok"],
        "pipeline_entry": ch["pipeline_ok"],
        "response_wrapper": ch["response_wrapper_ok"],
        "result_summary": ch["summary_ok"],
        "task_descriptor": ch["task_descriptor_ok"],
        "example_payloads": ch["example_payloads_ok"],
        "self_check": _self_check_callables(
            ("build_rightmove_self_check_report", "run_rightmove_self_check")
        ),
    }


def build_rightmove_capability_map() -> dict[str, Any]:
    """
    Structured capability table for router / chat / API consumers (no network I/O).

    Values derive from ``build_rightmove_self_check_report`` plus self-check entrypoints.
    """
    supported_modes: list[str] = []
    if _self_check_callable("get_supported_rightmove_modes"):
        try:
            supported_modes = list(get_supported_rightmove_modes())
        except Exception:
            supported_modes = []

    return {
        "platform": RIGHTMOVE_PLATFORM,
        "module": "scraper",
        "capabilities": _build_rightmove_capabilities_from_self_check(),
        "supported_modes": supported_modes,
        "notes": [
            "rightmove only",
            "requests + beautifulsoup version",
            "no playwright yet",
        ],
    }


def get_rightmove_capability_status(name: str | None) -> dict[str, Any]:
    """
    Look up one capability by name. Unknown or empty names return ``supported: False``
    and ``error: "unknown capability"`` (no exception).
    """
    caps = build_rightmove_capability_map()["capabilities"]
    if not isinstance(name, str) or not name.strip():
        return {"name": name, "supported": False, "error": "unknown capability"}
    key = name.strip()
    if key not in caps:
        return {"name": key, "supported": False, "error": "unknown capability"}
    return {"name": key, "supported": caps[key], "error": None}


RIGHTMOVE_SNAPSHOT_SECTIONS: tuple[str, ...] = (
    "supported_modes",
    "config",
    "task_descriptor",
    "capability_map",
    "self_check",
)


def _build_rightmove_config_snapshot() -> dict[str, Any]:
    """Lightweight config summary (no full header values)."""
    return {
        "default_limit": DEFAULT_LIMIT,
        "default_pages": DEFAULT_PAGES,
        "default_batch_limit": DEFAULT_BATCH_LIMIT,
        "default_timeout": DEFAULT_TIMEOUT,
        "default_output_file": DEFAULT_OUTPUT_FILE,
        "headers_keys": list(DEFAULT_HEADERS.keys()),
    }


def build_rightmove_module_snapshot() -> dict[str, Any]:
    """
    Aggregate module metadata for router / chat / API (no network I/O).

    Reuses task descriptor, capability map, and self-check report builders.
    """
    supported_modes: list[str] = []
    if _self_check_callable("get_supported_rightmove_modes"):
        try:
            supported_modes = list(get_supported_rightmove_modes())
        except Exception:
            supported_modes = []

    return {
        "platform": RIGHTMOVE_PLATFORM,
        "module": "scraper",
        "supported_modes": supported_modes,
        "config": _build_rightmove_config_snapshot(),
        "task_descriptor": build_rightmove_task_descriptor(),
        "capability_map": build_rightmove_capability_map(),
        "self_check": build_rightmove_self_check_report(),
    }


def get_rightmove_snapshot_section(name: str | None) -> dict[str, Any]:
    """
    Return one slice of ``build_rightmove_module_snapshot``. Unknown or empty
    section names yield ``supported: False`` and ``error: "unknown snapshot section"`` (no exception).
    """
    if not isinstance(name, str) or not name.strip():
        return {
            "name": name,
            "supported": False,
            "data": None,
            "error": "unknown snapshot section",
        }
    key = name.strip()
    if key not in RIGHTMOVE_SNAPSHOT_SECTIONS:
        return {
            "name": key,
            "supported": False,
            "data": None,
            "error": "unknown snapshot section",
        }
    data = build_rightmove_module_snapshot()[key]
    return {"name": key, "supported": True, "data": data, "error": None}


RIGHTMOVE_MANIFEST_VERSION = "v1"
RIGHTMOVE_RECOMMENDED_ENTRY = "execute_rightmove_pipeline"

RIGHTMOVE_MANIFEST_ENTRY_KEYS: tuple[str, ...] = (
    "single_scrape",
    "search_links",
    "batch_single_page",
    "batch_multi_page",
    "service_entry",
    "payload_entry",
    "pipeline_entry",
    "export_entry",
    "save_entry",
    "load_entry",
)


def _build_rightmove_module_entries() -> dict[str, str]:
    """Stable public function names for each manifest slot (strings only, no I/O)."""
    return {
        "single_scrape": "scrape_rightmove_listing",
        "search_links": "extract_rightmove_listing_links",
        "batch_single_page": "scrape_rightmove_search_results",
        "batch_multi_page": "scrape_rightmove_search_results_from_pages",
        "service_entry": "run_rightmove_service",
        "payload_entry": "run_rightmove_service_from_payload",
        "pipeline_entry": "execute_rightmove_pipeline",
        "export_entry": "export_rightmove_results",
        "save_entry": "save_rightmove_export_to_json",
        "load_entry": "load_rightmove_export_from_json",
    }


def build_rightmove_module_manifest() -> dict[str, Any]:
    """
    Human- and machine-readable entry map for router / chat / API (no network I/O).

    ``supported_modes`` comes from ``build_rightmove_module_snapshot`` (reuses mode list).
    """
    supported_modes = build_rightmove_module_snapshot()["supported_modes"]
    rec = RIGHTMOVE_RECOMMENDED_ENTRY
    return {
        "platform": RIGHTMOVE_PLATFORM,
        "module": "scraper",
        "version": RIGHTMOVE_MANIFEST_VERSION,
        "recommended_entry": rec,
        "entries": _build_rightmove_module_entries(),
        "input_styles": [
            "raw url arguments",
            "service mode + url",
            "payload dict",
        ],
        "supported_modes": supported_modes,
        "notes": [
            "rightmove only",
            "requests + beautifulsoup version",
            "no playwright yet",
            "recommended top-level entry is execute_rightmove_pipeline",
        ],
    }


def get_rightmove_manifest_entry(name: str | None) -> dict[str, Any]:
    """
    Resolve one manifest slot to its public function name string. Unknown or empty
    names return ``supported: False`` and ``error: "unknown manifest entry"`` (no exception).
    """
    entries = _build_rightmove_module_entries()
    if not isinstance(name, str) or not name.strip():
        return {"name": name, "supported": False, "data": None, "error": "unknown manifest entry"}
    key = name.strip()
    if key not in entries:
        return {"name": key, "supported": False, "data": None, "error": "unknown manifest entry"}
    return {"name": key, "supported": True, "data": entries[key], "error": None}


RIGHTMOVE_PHASE_ID = "phase_2"
RIGHTMOVE_NEXT_PHASE_ID = "phase_3_contract_analysis"


def build_rightmove_module_status() -> dict[str, Any]:
    """
    Phase 2 completion marker and readiness gate (no network I/O).

    ``ready_for_next_phase`` is False when ``build_rightmove_self_check_report()`` reports ``ok`` False.
    """
    report = build_rightmove_self_check_report()
    self_ok = bool(report.get("ok"))
    ready = self_ok
    status_label = "completed" if self_ok else "incomplete"
    core_ready: dict[str, bool] = {
        "scraper": True,
        "batch": True,
        "multi_page": True,
        "export": True,
        "save_load": True,
        "service_layer": True,
        "payload_entry": True,
        "pipeline_entry": True,
    }
    return {
        "platform": RIGHTMOVE_PLATFORM,
        "module": "scraper",
        "phase": RIGHTMOVE_PHASE_ID,
        "status": status_label,
        "ready_for_next_phase": ready,
        "next_phase": RIGHTMOVE_NEXT_PHASE_ID,
        "core_ready": core_ready,
    }


def is_rightmove_module_ready() -> bool:
    """True when ``build_rightmove_module_status()`` has ``ready_for_next_phase`` True."""
    return bool(build_rightmove_module_status()["ready_for_next_phase"])


def _normalize_listing_result(result: dict[str, Any]) -> dict[str, Any]:
    """Strip strings, empty str → None for text fields; clean images; raw_text always str."""
    desc = result.get("description")
    if isinstance(desc, str) and not desc.strip():
        result["description"] = None
    for key in ("address", "property_type"):
        v = result.get(key)
        if v is None:
            continue
        if isinstance(v, str):
            s = v.strip()
            result[key] = s if s else None
        else:
            s = str(v).strip()
            result[key] = s if s else None

    imgs = result.get("images")
    if not isinstance(imgs, list):
        imgs = []
    seen: set[str] = set()
    clean_imgs: list[str] = []
    for x in imgs:
        if not x or not isinstance(x, str):
            continue
        s = x.strip()
        if not s or s in seen:
            continue
        seen.add(s)
        clean_imgs.append(s)
    result["images"] = clean_imgs

    rt = result.get("raw_text")
    if rt is None:
        result["raw_text"] = ""
    elif not isinstance(rt, str):
        result["raw_text"] = str(rt)

    return result


def _apply_parse_status(result: dict[str, Any]) -> None:
    """Set status to success or partial when not already error."""
    if result.get("status") == "error":
        return
    core = sum(
        1 for k in ("price", "address", "description") if result.get(k) is not None
    )
    if core >= 2:
        result["status"] = "success"
    else:
        result["status"] = "partial"
    result["error"] = None


def safe_get_text(node: Any) -> str | None:
    """Safely get stripped text from a Tag/string; missing node → None."""
    if node is None:
        return None
    try:
        if isinstance(node, Tag) or hasattr(node, "get_text"):
            t = node.get_text(separator=" ", strip=True)
        else:
            t = str(node).strip()
        t = " ".join(t.split()) if t else ""
        return t if t else None
    except Exception:
        return None


def clean_price(price_text: str | None) -> int | None:
    """Parse a price string to int monthly rent, e.g. '£1,200 pcm' -> 1200; fail → None."""
    if not price_text:
        return None
    s = str(price_text).strip()
    m = _PRICE_PCM_RE.search(s) or _PRICE_ANY_RE.search(s)
    if not m:
        digits = re.sub(r"[^\d]", "", s.split(".")[0])
        return int(digits) if digits else None
    num = m.group(1).replace(",", "")
    try:
        return int(float(num))
    except (TypeError, ValueError):
        return None


def extract_number(text: str | None, *, kind: str = "any") -> int | None:
    """
    Extract a leading integer from phrases like '2 bed', '1 bathroom'.
    kind: 'bed' | 'bath' | 'any' (bed first, then bath, then first plausible digit).
    """
    if not text:
        return None
    s = str(text).strip()
    try:
        if kind in ("bed", "bedroom", "any"):
            m = _BED_RE.search(s)
            if m:
                return int(m.group(1))
        if kind in ("bath", "bathroom", "any"):
            m = _BATH_RE.search(s)
            if m:
                return int(m.group(1))
        if kind == "any":
            m = re.search(r"\b(\d+)\b", s)
            if m:
                return int(m.group(1))
    except (TypeError, ValueError):
        return None
    return None


def first_non_empty(*values: Any) -> Any:
    """Return the first non-empty value (None / blank str / empty list / empty dict skipped)."""
    for v in values:
        if v is None:
            continue
        if isinstance(v, str) and not v.strip():
            continue
        if isinstance(v, (list, dict)) and len(v) == 0:
            continue
        return v
    return None


def safe_text(node: Any, default: str | None = None) -> str | None:
    """Compatibility: same as safe_get_text with optional default."""
    t = safe_get_text(node)
    return t if t is not None else default


def is_rightmove_url(url: str) -> bool:
    """True if URL host looks like rightmove.co.uk (simple check)."""
    try:
        host = urlparse(url).netloc.lower()
        return "rightmove.co.uk" in host
    except Exception:
        return False


def is_rightmove_search_url(url: str) -> bool:
    """True if URL looks like a Rightmove search / results page (heuristic)."""
    if not (url or "").strip():
        return False
    if not is_rightmove_url(url):
        return False
    try:
        p = urlparse(url.strip())
        path = (p.path or "").lower()
        q = (p.query or "").lower()
        if "property-to-rent" in path or "property-for-sale" in path:
            return True
        if "find.html" in path or "/find" in path or "/search" in path:
            return True
        if "find" in path and "property" in path:
            return True
        if "searchlocation" in q or "locationidentifier" in q:
            return True
    except Exception:
        return False
    return False


def normalize_rightmove_url(href: str, base_url: str | None = None) -> str | None:
    """
    Turn a possibly relative href into a canonical property detail URL, or None if invalid.

    Only accepts paths like /properties/<digits> (single listing).
    """
    if not href or not isinstance(href, str):
        return None
    h = href.strip()
    if not h or h.startswith("#") or h.lower().startswith("javascript:"):
        return None
    base = (base_url or "").strip() or "https://www.rightmove.co.uk/"
    full = urljoin(base, h)
    try:
        p = urlparse(full)
    except Exception:
        return None
    if "rightmove.co.uk" not in (p.netloc or "").lower():
        return None
    path = p.path or ""
    m = re.match(r"^/properties/(\d+)(?:/|$)", path, re.I)
    if not m:
        return None
    pid = m.group(1)
    return f"https://www.rightmove.co.uk/properties/{pid}"


def _collect_ld_json(soup: BeautifulSoup) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for tag in soup.find_all("script", type="application/ld+json"):
        raw = tag.string or tag.get_text() or ""
        raw = raw.strip()
        if not raw:
            continue
        try:
            data = json.loads(raw)
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        out.append(item)
            elif isinstance(data, dict):
                out.append(data)
        except json.JSONDecodeError:
            continue
    return out


def _extract_regex_hints_from_html(html: str) -> dict[str, Any]:
    """Pull price/bed/bath from raw HTML when JSON is embedded as text."""
    out: dict[str, Any] = {}
    if not html:
        return out
    for rx in _HTML_PRICE_HINTS:
        m = rx.search(html)
        if m:
            try:
                raw = m.group(1).replace(",", "")
                out["price_int"] = int(raw)
                break
            except (ValueError, IndexError):
                continue
    for rx in _HTML_BED_HINTS:
        m = rx.search(html)
        if m:
            try:
                out["bedrooms"] = int(m.group(1))
                break
            except (ValueError, IndexError):
                continue
    for rx in _HTML_BATH_HINTS:
        m = rx.search(html)
        if m:
            try:
                out["bathrooms"] = int(m.group(1))
                break
            except (ValueError, IndexError):
                continue
    return out


def _extract_json_script_blocks(soup: BeautifulSoup) -> list[Any]:
    """Parse inline JSON from script tags (__NEXT_DATA__, application/json, large JSON blobs)."""
    parsed: list[Any] = []
    for tag in soup.find_all("script"):
        try:
            sid = (tag.get("id") or "").strip()
            typ = (tag.get("type") or "").strip().lower()
            raw = tag.string or tag.get_text() or ""
            raw = raw.strip()
            if not raw:
                continue
            if sid == "__NEXT_DATA__" or typ == "application/json" or (
                len(raw) > 80 and raw[0] in "{["
            ):
                try:
                    parsed.append(json.loads(raw))
                except json.JSONDecodeError:
                    continue
        except Exception:
            continue
    return parsed


def _walk_dict_for_numbers(obj: Any, depth: int = 0) -> dict[str, Any]:
    found: dict[str, Any] = {}
    if depth > 14:
        return found
    if isinstance(obj, dict):
        lower_keys = {str(k).lower(): (k, v) for k, v in obj.items()}
        for lk, (k, v) in lower_keys.items():
            if any(n in lk for n in ("price", "rent", "amount", "pcm")):
                if isinstance(v, (int, float)) and 0 < v < 10_000_000:
                    found.setdefault("price_num", int(v))
                elif isinstance(v, str):
                    pi = clean_price(v)
                    if pi is not None:
                        found.setdefault("price_num", pi)
            if any(n in lk for n in ("bedrooms", "beds", "bedroom", "numberofbedrooms")):
                if isinstance(v, (int, float)):
                    found.setdefault("bedrooms", int(v))
                elif isinstance(v, str):
                    n = extract_number(v, kind="bed")
                    if n is not None:
                        found.setdefault("bedrooms", n)
            if any(n in lk for n in ("bathrooms", "baths", "bathroom", "numberofbathrooms")):
                if isinstance(v, (int, float)):
                    found.setdefault("bathrooms", int(v))
                elif isinstance(v, str):
                    n = extract_number(v, kind="bath")
                    if n is not None:
                        found.setdefault("bathrooms", n)
            if lk in ("propertytype", "property_type", "type") and isinstance(v, str):
                m = _PROPERTY_TYPE_RE.search(v)
                if m:
                    found.setdefault("property_type", m.group(1).lower())
        for v in obj.values():
            found.update(_walk_dict_for_numbers(v, depth + 1))
    elif isinstance(obj, list):
        for item in obj[:80]:
            found.update(_walk_dict_for_numbers(item, depth + 1))
    return found


def _merge_script_trees(trees: list[Any]) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for tree in trees:
        merged.update(_walk_dict_for_numbers(tree))
    return merged


def _extract_from_ld_json(items: list[dict[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {"images_extra": []}
    for item in items:
        if not isinstance(item, dict):
            continue
        scanned = _walk_dict_for_numbers(item)
        if scanned.get("price_num") is not None:
            out.setdefault("price_int", scanned["price_num"])
        if scanned.get("bedrooms") is not None:
            out.setdefault("bedrooms", scanned["bedrooms"])
        if scanned.get("bathrooms") is not None:
            out.setdefault("bathrooms", scanned["bathrooms"])
        if scanned.get("property_type"):
            out.setdefault("property_type", scanned["property_type"])

        name = item.get("name") or item.get("headline")
        if name and not out.get("title"):
            out["title"] = safe_get_text(name)
        desc = item.get("description")
        if desc and not out.get("description"):
            out["description"] = safe_get_text(desc)
        addr = item.get("address")
        if isinstance(addr, dict):
            parts = [
                addr.get("streetAddress"),
                addr.get("addressLocality"),
                addr.get("addressRegion"),
                addr.get("postalCode"),
            ]
            line = ", ".join(safe_get_text(p) for p in parts if safe_get_text(p))
            if line:
                out.setdefault("address", line)
        offers = item.get("offers")
        if isinstance(offers, dict):
            price = offers.get("price") or offers.get("lowPrice") or offers.get("highPrice")
            if isinstance(price, (int, float)):
                out.setdefault("price_int", int(price))
            elif isinstance(price, str):
                pi = clean_price(price)
                if pi is not None:
                    out.setdefault("price_int", pi)
        img = item.get("image")
        if img:
            extra: list[str] = out["images_extra"]
            if isinstance(img, str):
                extra.append(img)
            elif isinstance(img, list):
                extra.extend(str(x) for x in img if x)
        num_rooms = item.get("numberOfRooms")
        if isinstance(num_rooms, (int, float)) and out.get("bedrooms") is None:
            out.setdefault("bedrooms", int(num_rooms))

        cat = item.get("category")
        if isinstance(cat, str) and not out.get("property_type"):
            m = _PROPERTY_TYPE_RE.search(cat)
            if m:
                out["property_type"] = m.group(1).lower()
    return out


def _try_next_data(soup: BeautifulSoup) -> dict[str, Any]:
    out: dict[str, Any] = {}
    tag = soup.find("script", id="__NEXT_DATA__")
    if not tag:
        return out
    raw = tag.string or tag.get_text() or ""
    raw = raw.strip()
    if not raw:
        return out
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return out
    scanned = _walk_dict_for_numbers(data)
    if scanned.get("price_num") is not None:
        out["price_int"] = scanned["price_num"]
    if scanned.get("bedrooms") is not None:
        out["bedrooms"] = scanned["bedrooms"]
    if scanned.get("bathrooms") is not None:
        out["bathrooms"] = scanned["bathrooms"]
    if scanned.get("property_type"):
        out["property_type"] = scanned["property_type"]
    return out


def _regex_counts_from_text(text: str) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if not text:
        return out
    nbed = extract_number(text, kind="bed")
    if nbed is not None:
        out["bedrooms"] = nbed
    nbath = extract_number(text, kind="bath")
    if nbath is not None:
        out["bathrooms"] = nbath
    pm = _PRICE_PCM_RE.search(text) or _PRICE_ANY_RE.search(text)
    if pm:
        pi = clean_price(pm.group(0))
        if pi is not None:
            out["price_int"] = pi
    ptm = _PROPERTY_TYPE_RE.search(text)
    if ptm:
        out["property_type"] = ptm.group(1).lower()
    return out


def _html_selectors_price(soup: BeautifulSoup) -> int | None:
    selectors = (
        '[class*="PropertyPrice"]',
        '[class*="price"]',
        '[data-test*="price"]',
        "[itemprop=price]",
    )
    for sel in selectors:
        try:
            el = soup.select_one(sel)
        except Exception:
            el = None
        if not el:
            continue
        t = safe_get_text(el)
        if t:
            p = clean_price(t)
            if p is not None:
                return p
    return None


def _html_selectors_address(soup: BeautifulSoup) -> str | None:
    for sel in (
        '[class*="Address"]',
        '[class*="address"]',
        "[itemprop=streetAddress]",
        '[class*="propertyHeader"] h1',
        "h1",
    ):
        try:
            el = soup.select_one(sel)
        except Exception:
            el = None
        if not el:
            continue
        t = safe_get_text(el)
        if t and len(t) > 8:
            return t
    meta = soup.find("meta", property="og:title")
    if meta and meta.get("content"):
        t = safe_get_text(meta.get("content"))
        if t:
            return t
    return None


def _html_selectors_description(soup: BeautifulSoup) -> str | None:
    for sel in (
        '[class*="Description"]',
        '[class*="description"]',
        '[class*="About"]',
        "article",
        "main",
    ):
        try:
            el = soup.select_one(sel)
        except Exception:
            el = None
        if not el:
            continue
        t = safe_get_text(el)
        if t and len(t) > 120:
            return t[:20000]
    return None


def _html_selectors_property_details(soup: BeautifulSoup) -> dict[str, Any]:
    """Key features / info strip: text used for bed/bath/type."""
    out: dict[str, Any] = {}
    chunks: list[str] = []
    for sel in (
        '[class*="PropertyInformation"]',
        '[class*="KeyFeatures"]',
        '[class*="keyFeatures"]',
        '[class*="Features"]',
        '[class*="propertyInformation"]',
    ):
        try:
            for el in soup.select(sel)[:5]:
                t = safe_get_text(el)
                if t:
                    chunks.append(t)
        except Exception:
            continue
    blob = " ".join(chunks)[:12000]
    if blob:
        out.update(_regex_counts_from_text(blob))
    return out


def _html_fallback(soup: BeautifulSoup, base_url: str) -> dict[str, Any]:
    out: dict[str, Any] = {}
    h1 = soup.find("h1")
    if h1:
        out["heading"] = safe_get_text(h1)
    og_title = soup.find("meta", property="og:title")
    if og_title and og_title.get("content"):
        out.setdefault("og_title", safe_get_text(og_title.get("content")))
    og_desc = soup.find("meta", property="og:description")
    if og_desc and og_desc.get("content"):
        out.setdefault("og_description", safe_get_text(og_desc.get("content")))

    for sel in (
        '[class*="PropertyInformation"]',
        '[class*="propertyHeader"]',
        '[class*="_price"]',
        "article",
        "main",
    ):
        try:
            block = soup.select_one(sel)
        except Exception:
            block = None
        if block:
            t = safe_get_text(block)
            if t and len(t) > 20:
                merged = _regex_counts_from_text(t)
                out.update({k: v for k, v in merged.items() if k not in out})
            break

    seen: set[str] = set()
    images: list[str] = []
    for img in soup.find_all("img"):
        for attr in ("src", "data-src", "data-original", "data-lazy"):
            src = img.get(attr)
            if not src or not isinstance(src, str):
                continue
            src = src.strip().split()[0] if src else ""
            if not src.startswith("http"):
                src = urljoin(base_url, src)
            low = src.lower()
            if "rightmove" not in low and "media" not in low:
                continue
            if src in seen:
                continue
            seen.add(src)
            images.append(src)
            if len(images) >= 50:
                break
        if len(images) >= 50:
            break
    if images:
        out["images"] = images
    return out


def _urls_from_raw_html(html: str) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for m in _MEDIA_IMG_RE.finditer(html or ""):
        u = m.group(0).rstrip("\\\"'")
        if u not in seen:
            seen.add(u)
            out.append(u)
        if len(out) >= 40:
            break
    return out


def _visible_body_text(soup: BeautifulSoup) -> str:
    """Main visible text for raw_text (scripts/styles removed)."""
    try:
        soup2 = BeautifulSoup(str(soup), "html.parser")
        for bad in soup2(["script", "style", "noscript", "svg"]):
            try:
                bad.decompose()
            except Exception:
                continue
        body = soup2.find("body")
        blob = safe_get_text(body) if body else safe_get_text(soup2)
        if blob:
            return blob[:200000]
    except Exception:
        pass
    return ""


def _merge_description(*parts: str | None) -> str | None:
    texts = [p.strip() for p in parts if p and str(p).strip()]
    if not texts:
        return None
    return "\n\n".join(dict.fromkeys(texts))


def parse_rightmove_listing(url: str) -> dict[str, Any]:
    """
    Fetch a single Rightmove property page and return structured fields.

    Order: JSON / embedded script data → regex hints on HTML → HTML selectors → None.
    Does not raise on failure; returns unified dict with status/error and normalized fields.
    """
    result = build_empty_result(url)
    u = result["url"]
    if not u or not is_rightmove_url(u):
        result["status"] = "error"
        result["error"] = "Invalid or empty Rightmove URL"
        return _normalize_listing_result(result)

    try:
        r = requests.get(u, headers=DEFAULT_HEADERS, timeout=DEFAULT_TIMEOUT)
        r.raise_for_status()
        html = r.text or ""

        soup = BeautifulSoup(html, "html.parser")
        # Snapshot visible text before any soup mutation (description path decomposes scripts).
        visible_snapshot = _visible_body_text(BeautifulSoup(html, "html.parser"))

        ld_items = _collect_ld_json(soup)
        ld_out = _extract_from_ld_json(ld_items)
        script_trees = _extract_json_script_blocks(soup)
        script_merged = _merge_script_trees(script_trees)
        next_out = _try_next_data(soup)
        regex_html = _extract_regex_hints_from_html(html)

        body_text = ""
        try:
            body = soup.find("body")
            body_text = safe_get_text(body) or ""
        except Exception:
            body_text = ""

        merged_regex = _regex_counts_from_text(body_text)
        details_strip = _html_selectors_property_details(soup)
        fallback = _html_fallback(soup, u)

        price_val = first_non_empty(
            ld_out.get("price_int"),
            next_out.get("price_int"),
            script_merged.get("price_num"),
            regex_html.get("price_int"),
            merged_regex.get("price_int"),
            details_strip.get("price_int"),
            fallback.get("price_int"),
            _html_selectors_price(soup),
        )
        if price_val is not None:
            try:
                result["price"] = int(price_val)
            except (TypeError, ValueError):
                result["price"] = None

        beds = first_non_empty(
            ld_out.get("bedrooms"),
            next_out.get("bedrooms"),
            script_merged.get("bedrooms"),
            regex_html.get("bedrooms"),
            merged_regex.get("bedrooms"),
            details_strip.get("bedrooms"),
            fallback.get("bedrooms"),
        )
        if beds is None and body_text:
            beds = extract_number(body_text[:5000], kind="bed")
        if beds is not None:
            try:
                result["bedrooms"] = int(beds)
            except (TypeError, ValueError):
                pass

        baths = first_non_empty(
            ld_out.get("bathrooms"),
            next_out.get("bathrooms"),
            script_merged.get("bathrooms"),
            regex_html.get("bathrooms"),
            merged_regex.get("bathrooms"),
            details_strip.get("bathrooms"),
            fallback.get("bathrooms"),
        )
        if baths is None and body_text:
            baths = extract_number(body_text[:5000], kind="bath")
        if baths is not None:
            try:
                result["bathrooms"] = int(baths)
            except (TypeError, ValueError):
                pass

        addr = first_non_empty(
            ld_out.get("address"),
            _html_selectors_address(soup),
            safe_get_text(soup.find("address")),
            fallback.get("heading"),
        )
        if not addr:
            try:
                meta_addr = soup.find("meta", attrs={"name": re.compile(r"location|address", re.I)})
                if meta_addr and meta_addr.get("content"):
                    addr = safe_get_text(meta_addr.get("content"))
            except Exception:
                pass
        result["address"] = addr

        ptype = first_non_empty(
            ld_out.get("property_type"),
            next_out.get("property_type"),
            script_merged.get("property_type"),
            merged_regex.get("property_type"),
            details_strip.get("property_type"),
            fallback.get("property_type"),
        )
        if not ptype and body_text:
            pm = _PROPERTY_TYPE_RE.search(body_text[:4000])
            if pm:
                ptype = pm.group(1).lower()
        result["property_type"] = ptype

        desc = _merge_description(
            ld_out.get("description"),
            fallback.get("og_description"),
        )
        if not desc:
            desc = fallback.get("og_description")
        if not desc:
            desc = _html_selectors_description(soup)
        if not desc:
            try:
                for bad in soup(["script", "style", "noscript"]):
                    bad.decompose()
                main = soup.find("main") or soup.find("article") or soup.body
                blob = safe_get_text(main) if main else safe_get_text(soup)
                if blob and len(blob) > 80:
                    desc = blob[:15000]
            except Exception:
                desc = None
        result["description"] = desc

        imgs: list[str] = list(ld_out.get("images_extra") or [])
        for im in fallback.get("images") or []:
            if im and im not in imgs:
                imgs.append(im)
        for im in _urls_from_raw_html(html):
            if im not in imgs:
                imgs.append(im)
        seen_i: set[str] = set()
        deduped: list[str] = []
        for im in imgs:
            if im in seen_i:
                continue
            seen_i.add(im)
            deduped.append(im)
        result["images"] = deduped[:60]

        result["raw_text"] = visible_snapshot if visible_snapshot else (html[:200000] if html else "")

        _normalize_listing_result(result)
        _apply_parse_status(result)
        return result
    except Exception as exc:
        err = build_empty_result(url)
        err["status"] = "error"
        msg = str(exc).strip() or "Request or parse failed"
        err["error"] = msg[:500]
        return _normalize_listing_result(err)


def scrape_rightmove_listing(url: str) -> dict[str, Any]:
    """
    Public entry for a single property URL (list/batch flows should call this per link).

    Validates URL, then delegates to parse_rightmove_listing. Never raises.
    """
    raw = (url or "").strip()
    if not raw:
        out = build_empty_result(url)
        out["status"] = "error"
        out["error"] = "Empty URL"
        return _normalize_listing_result(out)
    if not is_rightmove_url(raw):
        out = build_empty_result(url)
        out["status"] = "error"
        out["error"] = "Not a Rightmove URL"
        return _normalize_listing_result(out)
    try:
        return parse_rightmove_listing(raw)
    except Exception as exc:
        out = build_empty_result(url)
        out["status"] = "error"
        out["error"] = (str(exc).strip() or "Request or parse failed")[:500]
        return _normalize_listing_result(out)


def extract_rightmove_listing_links(search_url: str) -> list[str]:
    """
    Fetch a Rightmove search results page and collect unique property detail URLs in order.

    Does not fetch listing bodies. Returns [] on any failure or if URL is not a search page.
    """
    raw = (search_url or "").strip()
    if not raw:
        return []
    if not is_rightmove_url(raw):
        return []
    if not is_rightmove_search_url(raw):
        return []
    try:
        r = requests.get(raw, headers=DEFAULT_HEADERS, timeout=DEFAULT_TIMEOUT)
        r.raise_for_status()
        html = r.text or ""
    except Exception:
        return []
    try:
        soup = BeautifulSoup(html, "html.parser")
    except Exception:
        return []
    out: list[str] = []
    seen: set[str] = set()
    try:
        for a in soup.find_all("a", href=True):
            href = a.get("href")
            if not href or not isinstance(href, str):
                continue
            normalized = normalize_rightmove_url(href, raw)
            if not normalized:
                continue
            if normalized in seen:
                continue
            seen.add(normalized)
            out.append(normalized)
    except Exception:
        return []
    return out


# Rightmove UK search results: ~24 listings per page; `index` is the 0-based offset.
_RIGHTMOVE_SEARCH_PAGE_SIZE = 24


def normalize_page_count(pages: int) -> int:
    """Clamp pages: invalid or <= 0 → 1; cap at ``DEFAULT_BATCH_LIMIT`` (simple v1)."""
    try:
        n = int(pages)
    except (TypeError, ValueError):
        return 1
    if n <= 0:
        return 1
    return min(n, DEFAULT_BATCH_LIMIT)


def build_rightmove_search_page_url(search_url: str, page: int) -> str:
    """
    Build the search results URL for a given 1-based page index.

    page <= 1: return original search_url unchanged.
    page >= 2: set or replace query param ``index`` to (page - 1) * 24 (simple offset).
    """
    raw = (search_url or "").strip()
    if not raw:
        return ""
    try:
        p = int(page)
    except (TypeError, ValueError):
        return raw
    if p <= 1:
        return raw
    offset = (p - 1) * _RIGHTMOVE_SEARCH_PAGE_SIZE
    try:
        parsed = urlparse(raw)
        pairs = list(parse_qsl(parsed.query, keep_blank_values=True))
        found_index = False
        new_pairs: list[tuple[str, str]] = []
        for k, v in pairs:
            if k.lower() == "index":
                new_pairs.append((k, str(offset)))
                found_index = True
            else:
                new_pairs.append((k, v))
        if not found_index:
            new_pairs.append(("index", str(offset)))
        new_query = urlencode(new_pairs, doseq=True)
        return urlunparse(
            (parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, parsed.fragment)
        )
    except Exception:
        return raw


def extract_rightmove_listing_links_from_pages(search_url: str, pages: int = DEFAULT_PAGES) -> list[str]:
    """
    Fetch up to ``pages`` search result pages and merge listing detail URLs.

    Order is preserved; duplicates are skipped (first occurrence wins). Never raises;
    returns [] on bad URL or if nothing could be collected. Failed pages are skipped.
    """
    raw = (search_url or "").strip()
    if not raw:
        return []
    if not is_rightmove_url(raw) or not is_rightmove_search_url(raw):
        return []
    try:
        n = normalize_page_count(pages)
    except Exception:
        n = 1
    merged: list[str] = []
    seen: set[str] = set()
    for page in range(1, n + 1):
        try:
            page_url = build_rightmove_search_page_url(raw, page)
            if not (page_url or "").strip():
                continue
            links = extract_rightmove_listing_links(page_url)
            if not isinstance(links, list):
                continue
            for link in links:
                if not isinstance(link, str) or not link.strip():
                    continue
                if link in seen:
                    continue
                seen.add(link)
                merged.append(link)
        except Exception:
            continue
    return merged


def safe_limit(limit: int) -> int:
    """Clamp batch size: invalid or non-positive → ``DEFAULT_BATCH_LIMIT``; otherwise at least 1."""
    try:
        n = int(limit)
    except (TypeError, ValueError):
        return DEFAULT_BATCH_LIMIT
    if n <= 0:
        return DEFAULT_BATCH_LIMIT
    return max(1, n)


def scrape_rightmove_search_results(search_url: str, limit: int = DEFAULT_BATCH_LIMIT) -> list[dict[str, Any]]:
    """
    Search page → listing links → scrape_rightmove_listing per link (sequential, no concurrency).

    Returns a list of the same dict shape as scrape_rightmove_listing. Never raises.
    """
    raw = (search_url or "").strip()
    if not raw:
        return []
    if not is_rightmove_url(raw) or not is_rightmove_search_url(raw):
        return []
    lim = safe_limit(limit)
    try:
        links = extract_rightmove_listing_links(raw)
    except Exception:
        return []
    if not links:
        return []
    links = links[:lim]
    results: list[dict[str, Any]] = []
    for link in links:
        try:
            item = scrape_rightmove_listing(link)
            if not isinstance(item, dict):
                raise TypeError("expected dict from scrape_rightmove_listing")
            results.append(item)
        except Exception as exc:
            err = build_empty_result(link)
            err["status"] = "error"
            err["error"] = (str(exc).strip() or "Batch scrape failed for this URL")[:500]
            results.append(_normalize_listing_result(err))
    return results


def _multi_page_batch_limit(limit: Any) -> int:
    """Invalid or non-positive limit → ``DEFAULT_LIMIT``; otherwise positive int, at least 1."""
    try:
        n = int(limit)
    except (TypeError, ValueError):
        return DEFAULT_LIMIT
    if n <= 0:
        return DEFAULT_LIMIT
    return max(1, n)


def scrape_rightmove_search_results_from_pages(
    search_url: str, pages: int = DEFAULT_PAGES, limit: int = DEFAULT_LIMIT
) -> list[dict[str, Any]]:
    """
    Multi-page search → merged listing links → scrape_rightmove_listing per link (sequential).

    Same dict shape as scrape_rightmove_listing. Never raises.
    """
    raw = (search_url or "").strip()
    if not raw:
        return []
    if not is_rightmove_url(raw) or not is_rightmove_search_url(raw):
        return []
    try:
        n_pages = normalize_page_count(pages)
    except Exception:
        n_pages = 1
    lim = _multi_page_batch_limit(limit)
    try:
        links = extract_rightmove_listing_links_from_pages(raw, n_pages)
    except Exception:
        return []
    if not links:
        return []
    links = links[:lim]
    results: list[dict[str, Any]] = []
    for link in links:
        try:
            item = scrape_rightmove_listing(link)
            if not isinstance(item, dict):
                raise TypeError("expected dict from scrape_rightmove_listing")
            results.append(item)
        except Exception as exc:
            err = build_empty_result(link)
            err["status"] = "error"
            err["error"] = (str(exc).strip() or "Batch scrape failed for this URL")[:500]
            results.append(_normalize_listing_result(err))
    return results


def _numeric_price_value(value: Any) -> float | None:
    """int/float price only; bool excluded."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def is_valid_listing_result(item: dict[str, Any]) -> bool:
    """True if a single scrape dict is usable for downstream analysis (simple rules)."""
    if not isinstance(item, dict):
        return False
    if item.get("status") == "error":
        return False
    url = item.get("url")
    if not url or not str(url).strip():
        return False
    has_price = _numeric_price_value(item.get("price")) is not None
    has_addr = bool(str(item.get("address") or "").strip())
    has_desc = bool(str(item.get("description") or "").strip())
    if not (has_price or has_addr or has_desc):
        return False
    return True


def clean_rightmove_results(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep only valid listing dicts, original order."""
    if not results:
        return []
    out: list[dict[str, Any]] = []
    for r in results:
        if isinstance(r, dict) and is_valid_listing_result(r):
            out.append(r)
    return out


def summarize_rightmove_results(results: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Summary stats over a batch list (typically raw output from scrape_rightmove_search_results).

    total_* / status counts use all items; avg/min/max price use numeric prices from valid rows only.
    """
    empty = {
        "total_results": 0,
        "valid_results": 0,
        "success_count": 0,
        "partial_count": 0,
        "error_count": 0,
        "with_price_count": 0,
        "with_address_count": 0,
        "with_description_count": 0,
        "avg_price": None,
        "min_price": None,
        "max_price": None,
    }
    if not results:
        return dict(empty)

    total = len(results)
    valid_n = 0
    success_count = 0
    partial_count = 0
    error_count = 0
    with_price_count = 0
    with_address_count = 0
    with_description_count = 0
    price_samples: list[float] = []

    for r in results:
        if not isinstance(r, dict):
            continue
        st = r.get("status")
        if st == "success":
            success_count += 1
        elif st == "partial":
            partial_count += 1
        elif st == "error":
            error_count += 1

        if is_valid_listing_result(r):
            valid_n += 1
            npv = _numeric_price_value(r.get("price"))
            if npv is not None:
                price_samples.append(npv)

        if _numeric_price_value(r.get("price")) is not None:
            with_price_count += 1
        if str(r.get("address") or "").strip():
            with_address_count += 1
        if str(r.get("description") or "").strip():
            with_description_count += 1

    avg_price: float | None = None
    min_price: float | None = None
    max_price: float | None = None
    if price_samples:
        avg_price = round(sum(price_samples) / len(price_samples))
        min_price = round(min(price_samples))
        max_price = round(max(price_samples))

    return {
        "total_results": total,
        "valid_results": valid_n,
        "success_count": success_count,
        "partial_count": partial_count,
        "error_count": error_count,
        "with_price_count": with_price_count,
        "with_address_count": with_address_count,
        "with_description_count": with_description_count,
        "avg_price": avg_price,
        "min_price": min_price,
        "max_price": max_price,
    }


def export_rightmove_results(search_url: str, results: Any) -> dict[str, Any]:
    """
    Assemble a stable export payload: raw batch rows, cleaned rows, and summary.

    Does not fetch; only wraps clean_rightmove_results + summarize_rightmove_results.
    Tolerates bad inputs; never raises.
    """
    if isinstance(search_url, str):
        su = search_url.strip()
    elif search_url is None:
        su = ""
    else:
        su = str(search_url).strip()

    if results is None or not isinstance(results, list):
        raw_list: list[Any] = []
    else:
        raw_list = list(results)

    results_out = [x for x in raw_list if isinstance(x, dict)]

    empty_summary: dict[str, Any] = {
        "total_results": 0,
        "valid_results": 0,
        "success_count": 0,
        "partial_count": 0,
        "error_count": 0,
        "with_price_count": 0,
        "with_address_count": 0,
        "with_description_count": 0,
        "avg_price": None,
        "min_price": None,
        "max_price": None,
    }

    try:
        cleaned = clean_rightmove_results(raw_list)
    except Exception:
        cleaned = []

    try:
        summary = summarize_rightmove_results(raw_list)
        if not isinstance(summary, dict):
            summary = dict(empty_summary)
    except Exception:
        summary = dict(empty_summary)

    return {
        "platform": RIGHTMOVE_PLATFORM,
        "search_url": su,
        "results": results_out,
        "cleaned_results": cleaned,
        "summary": summary,
    }


def ensure_parent_dir(file_path: str) -> None:
    """Create parent directory for file_path if missing (best-effort, no raise)."""
    if not file_path or not isinstance(file_path, str):
        return
    try:
        parent = Path(file_path).expanduser().resolve().parent
        if str(parent) and not parent.is_dir():
            parent.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass


def save_rightmove_export_to_json(export_data: dict, file_path: str) -> bool:
    """
    Write export dict from export_rightmove_results to a UTF-8 JSON file.

    Returns True on success; False on invalid args or I/O errors (never raises).
    """
    if not file_path or not isinstance(file_path, str):
        return False
    fp = file_path.strip()
    if not fp:
        return False
    if not isinstance(export_data, dict):
        return False
    try:
        ensure_parent_dir(fp)
        with open(fp, "w", encoding="utf-8") as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False


def _normalize_loaded_export(data: dict[str, Any]) -> dict[str, Any]:
    """Merge raw JSON dict into the stable export shape; missing keys use defaults."""
    su_raw = data.get("search_url")
    if isinstance(su_raw, str):
        su = su_raw.strip()
    elif su_raw is None:
        su = ""
    else:
        su = str(su_raw).strip()

    out = build_empty_rightmove_export(su)
    out["platform"] = str(data.get("platform") or RIGHTMOVE_PLATFORM)

    res = data.get("results")
    out["results"] = [x for x in (res if isinstance(res, list) else []) if isinstance(x, dict)]

    cr = data.get("cleaned_results")
    out["cleaned_results"] = [x for x in (cr if isinstance(cr, list) else []) if isinstance(x, dict)]

    sm = data.get("summary")
    if isinstance(sm, dict):
        for k in list(out["summary"].keys()):
            if k in sm:
                out["summary"][k] = sm[k]
    return out


def load_rightmove_export_from_json(file_path: str) -> dict[str, Any]:
    """
    Load a UTF-8 JSON file written by save_rightmove_export_to_json (or compatible).

    On any failure (empty path, missing file, invalid JSON, non-dict root), returns
    build_empty_rightmove_export() — never raises.
    """
    empty = build_empty_rightmove_export()
    if not file_path or not isinstance(file_path, str):
        return empty
    fp = file_path.strip()
    if not fp:
        return empty
    try:
        p = Path(fp)
        if not p.is_file():
            return empty
        with open(p, encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return build_empty_rightmove_export()
    if not isinstance(data, dict):
        return build_empty_rightmove_export()
    try:
        return _normalize_loaded_export(data)
    except Exception:
        return build_empty_rightmove_export()


def export_rightmove_results_from_pages(
    search_url: str, pages: int = DEFAULT_PAGES, limit: int = DEFAULT_LIMIT
) -> dict[str, Any]:
    """
    Multi-page batch scrape → stable export dict (reuses export_rightmove_results).

    Never raises; on failure returns build_empty_rightmove_export().
    """
    try:
        results = scrape_rightmove_search_results_from_pages(search_url, pages, limit)
    except Exception:
        return build_empty_rightmove_export()
    try:
        return export_rightmove_results(search_url, results)
    except Exception:
        return build_empty_rightmove_export()


def save_rightmove_results_from_pages(
    search_url: str, file_path: str, pages: int = DEFAULT_PAGES, limit: int = DEFAULT_LIMIT
) -> bool:
    """
    Multi-page export → UTF-8 JSON file (reuses save_rightmove_export_to_json).

    Returns True on success; False on invalid args or I/O errors (never raises).
    """
    try:
        export_data = export_rightmove_results_from_pages(search_url, pages, limit)
    except Exception:
        return False
    try:
        return save_rightmove_export_to_json(export_data, file_path)
    except Exception:
        return False


def _default_export_validation_result() -> dict[str, Any]:
    """Baseline validation payload (all checks failed)."""
    return {
        "is_valid": False,
        "platform_ok": False,
        "search_url_ok": False,
        "results_is_list": False,
        "cleaned_results_is_list": False,
        "summary_is_dict": False,
        "summary_has_core_fields": False,
        "results_count": 0,
        "cleaned_results_count": 0,
    }


def load_rightmove_results_from_pages_json(file_path: str) -> dict[str, Any]:
    """
    Load a multi-page export JSON file (same format as save_rightmove_results_from_pages).

    Delegates to load_rightmove_export_from_json; never raises.
    """
    try:
        return load_rightmove_export_from_json(file_path)
    except Exception:
        return build_empty_rightmove_export()


def validate_rightmove_export_data(export_data: Any) -> dict[str, Any]:
    """
    Minimal structural validation for a loaded export dict. Never raises.

    ``is_valid`` is True only when all key shape checks pass (simple v1 rules).
    """
    out = _default_export_validation_result()
    if not isinstance(export_data, dict):
        return out

    out["platform_ok"] = export_data.get("platform") == RIGHTMOVE_PLATFORM
    out["search_url_ok"] = isinstance(export_data.get("search_url"), str)

    res = export_data.get("results")
    out["results_is_list"] = isinstance(res, list)
    out["results_count"] = len(res) if isinstance(res, list) else 0

    cr = export_data.get("cleaned_results")
    out["cleaned_results_is_list"] = isinstance(cr, list)
    out["cleaned_results_count"] = len(cr) if isinstance(cr, list) else 0

    summ = export_data.get("summary")
    out["summary_is_dict"] = isinstance(summ, dict)
    if isinstance(summ, dict):
        out["summary_has_core_fields"] = all(k in summ for k in SUMMARY_CORE_FIELDS)
    else:
        out["summary_has_core_fields"] = False

    out["is_valid"] = (
        out["platform_ok"]
        and out["search_url_ok"]
        and out["results_is_list"]
        and out["cleaned_results_is_list"]
        and out["summary_is_dict"]
        and out["summary_has_core_fields"]
    )
    return out


def run_rightmove_service(
    mode: str,
    url: str,
    limit: int = DEFAULT_LIMIT,
    pages: int = DEFAULT_PAGES,
    output_file: str | None = None,
) -> dict[str, Any]:
    """
    Single entry point for Rightmove scrape flows (router/API/chat-friendly).

    Returns ``{ok, mode, data, error, meta}``; never raises.
    """
    m = ""
    u = ""
    try:
        m = _normalize_service_mode(mode)
        lim_n = normalize_limit_input(limit)
        pg_n = normalize_pages_input(pages)
        u = (url or "").strip() if isinstance(url, str) else str(url or "").strip()
        base_meta: dict[str, Any] = {
            "source": "service",
            "url": u,
            "limit": lim_n,
            "pages": pg_n,
        }

        ok_mode, _ = validate_rightmove_mode(m)
        td = get_rightmove_task_descriptor_by_mode(m)
        base_meta["task_supported"] = bool(td.get("supported"))
        if not ok_mode:
            return build_rightmove_response(
                False,
                m if m else None,
                None,
                "unsupported mode",
                base_meta,
            )

        ok_url, _ = validate_rightmove_url_input(url)
        if not ok_url:
            return build_rightmove_response(False, m, None, "empty url", base_meta)

        md = get_rightmove_mode_description(m)
        if md:
            base_meta["mode_description"] = md
        base_meta["summary_ready"] = True

        if m == "single":
            data = scrape_rightmove_listing(u)
            return build_rightmove_response(True, m, data, None, base_meta)

        if m == "search_links":
            data = extract_rightmove_listing_links(u)
            return build_rightmove_response(True, m, data, None, base_meta)

        if m == "batch":
            data = scrape_rightmove_search_results(u, lim_n)
            return build_rightmove_response(True, m, data, None, base_meta)

        if m == "multi_page_batch":
            data = scrape_rightmove_search_results_from_pages(u, pg_n, lim_n)
            return build_rightmove_response(True, m, data, None, base_meta)

        if m == "export":
            data = export_rightmove_results_from_pages(u, pg_n, lim_n)
            return build_rightmove_response(True, m, data, None, base_meta)

        if m == "save":
            ok_of, of_err = validate_output_file_input(output_file)
            if not ok_of:
                return build_rightmove_response(False, m, None, of_err, base_meta)
            of = output_file.strip() if isinstance(output_file, str) else str(output_file).strip()
            saved = save_rightmove_results_from_pages(u, of, pg_n, lim_n)
            sm = {**base_meta, "output_file": of}
            return build_rightmove_response(
                saved,
                m,
                {"saved": saved, "output_file": of},
                None if saved else "save failed",
                sm,
            )

        return build_rightmove_response(False, m, None, "unsupported mode", base_meta)
    except Exception as exc:
        mm = m if m else _normalize_service_mode(mode)
        u = (url or "").strip() if isinstance(url, str) else str(url or "").strip()
        lim_e = normalize_limit_input(limit)
        pg_e = normalize_pages_input(pages)
        err_meta: dict[str, Any] = {
            "source": "service",
            "url": u,
            "limit": lim_e,
            "pages": pg_e,
        }
        md_e = get_rightmove_mode_description(mm)
        if md_e:
            err_meta["mode_description"] = md_e
        return build_rightmove_response(
            False,
            mm if mm else None,
            None,
            (str(exc).strip() or "service error")[:500],
            err_meta,
        )


def normalize_rightmove_payload(payload: dict) -> dict[str, Any]:
    """
    Normalize a payload to keys ``mode``, ``url``, ``limit``, ``pages``, ``output_file``.

    Missing ``limit`` / ``pages`` use ``DEFAULT_LIMIT`` / ``DEFAULT_PAGES``; missing ``output_file`` → None.
    """
    mode_raw = payload.get("mode")
    m = _normalize_service_mode(mode_raw) if mode_raw is not None else ""

    u = payload.get("url")
    if isinstance(u, str):
        url_s = u.strip()
    elif u is None:
        url_s = ""
    else:
        url_s = str(u).strip()

    limit = normalize_limit_input(payload.get("limit"))
    pages = normalize_pages_input(payload.get("pages"))

    of = payload.get("output_file")
    if of is None:
        output_file = None
    elif isinstance(of, str):
        output_file = of.strip() or None
    else:
        output_file = str(of).strip() or None

    return {
        "mode": m,
        "url": url_s,
        "limit": limit,
        "pages": pages,
        "output_file": output_file,
    }


def run_rightmove_service_from_payload(payload: Any) -> dict[str, Any]:
    """
    Parse a request payload (typically a dict) and delegate to ``run_rightmove_service``.

    Same return shape as ``run_rightmove_service`` (includes ``meta``, ``source`` = ``payload``); never raises.
    """
    ok_pl, pl_err = validate_rightmove_payload_input(payload)
    if not ok_pl:
        return build_rightmove_response(
            False,
            None,
            None,
            pl_err or "invalid payload",
            {"source": "payload"},
        )
    try:
        mode_raw = payload.get("mode")
        m = _normalize_service_mode(mode_raw)
        if not m:
            return build_rightmove_response(
                False,
                None,
                None,
                "missing mode",
                {"source": "payload"},
            )

        if not validate_rightmove_url_input(payload.get("url"))[0]:
            return build_rightmove_response(
                False,
                m,
                None,
                "missing url",
                {"source": "payload", "url": ""},
            )

        n = normalize_rightmove_payload(payload)
        inner = run_rightmove_service(
            n["mode"],
            n["url"],
            limit=n["limit"],
            pages=n["pages"],
            output_file=n["output_file"],
        )
        pm = dict(inner.get("meta") or {})
        pm["source"] = "payload"
        pm["url"] = n["url"]
        pm["limit"] = n["limit"]
        pm["pages"] = n["pages"]
        if n["output_file"] is not None:
            pm["output_file"] = n["output_file"]
        pm["platform"] = RIGHTMOVE_PLATFORM
        return {**inner, "meta": pm}
    except Exception as exc:
        return build_rightmove_response(
            False,
            None,
            None,
            (str(exc).strip() or "payload error")[:500],
            {"source": "payload"},
        )


def merge_rightmove_meta(base_meta: dict[str, Any] | None, extra_meta: dict[str, Any] | None) -> dict[str, Any]:
    """Merge meta dicts; ``platform`` is always ``RIGHTMOVE_PLATFORM`` after merge."""
    out: dict[str, Any] = {"platform": RIGHTMOVE_PLATFORM}
    if base_meta and isinstance(base_meta, dict):
        out.update(base_meta)
    if extra_meta and isinstance(extra_meta, dict):
        out.update(extra_meta)
    out["platform"] = RIGHTMOVE_PLATFORM
    return out


def execute_rightmove_pipeline(payload: Any) -> dict[str, Any]:
    """
    Outermost entry: payload → ``run_rightmove_service_from_payload`` → ``meta.source`` = ``pipeline``.

    Same envelope as other layers; never raises.
    """
    ok_pl, pl_err = validate_rightmove_payload_input(payload)
    if not ok_pl:
        return build_rightmove_response(
            False,
            None,
            None,
            pl_err or "invalid payload",
            {"source": "pipeline"},
        )
    inner = run_rightmove_service_from_payload(payload)
    im = inner.get("meta") if isinstance(inner.get("meta"), dict) else {}
    merged = merge_rightmove_meta(im, {"source": "pipeline"})
    return {**inner, "meta": merged}


def run_single_listing_test(test_url: str) -> None:
    """Manual test: one listing scrape and core fields."""
    print("=== Single listing scrape ===")
    result = scrape_rightmove_listing(test_url)
    print("URL:", result.get("url") or test_url)
    print("Price:", result.get("price"))
    print("Address:", result.get("address"))
    print("Bedrooms:", result.get("bedrooms"))
    description = result.get("description") or ""
    print("Description:", description[:100])
    images = result.get("images") or []
    print("Images count:", len(images))
    print("Status:", result.get("status"))
    print("Error:", result.get("error"))


def run_search_links_test(search_url: str) -> None:
    """Manual test: listing links from search page (no detail fetch)."""
    print()
    print("=== Search page listing links ===")
    links = extract_rightmove_listing_links(search_url)
    print("Links count:", len(links))
    for link in links[:5]:
        print(link)


def run_batch_test(search_url: str, limit: int = 3) -> None:
    """Manual test: batch scrape + clean/summary (same coverage as before refactor)."""
    print()
    print(f"=== Batch search results (limit={limit}) ===")
    results = scrape_rightmove_search_results(search_url, limit)
    print("Batch results count:", len(results))
    for item in results:
        print("---")
        print("URL:", item.get("url"))
        print("Price:", item.get("price"))
        print("Address:", item.get("address"))
        print("Status:", item.get("status"))
    cleaned_results = clean_rightmove_results(results)
    summary = summarize_rightmove_results(results)
    print()
    print("=== Batch clean / summary ===")
    print("Cleaned results count:", len(cleaned_results))
    print("Summary:", summary)


def run_export_test(search_url: str, limit: int = 3) -> None:
    """Manual test: batch scrape + export payload."""
    print()
    print("=== Export ===")
    results = scrape_rightmove_search_results(search_url, limit)
    export_data = export_rightmove_results(search_url, results)
    print("Export keys:", list(export_data.keys()))
    print("Export summary:", export_data.get("summary"))
    print("Export cleaned_results count:", len(export_data.get("cleaned_results", [])))


def run_save_load_test(
    search_url: str, limit: int = 3, output_file: str = DEFAULT_OUTPUT_FILE
) -> None:
    """Manual test: export JSON save + load round-trip."""
    print()
    print("=== Save export JSON ===")
    results = scrape_rightmove_search_results(search_url, limit)
    export_data = export_rightmove_results(search_url, results)
    saved = save_rightmove_export_to_json(export_data, output_file)
    print("Save success:", saved)
    print("Output file:", output_file)
    print()
    print("=== Load export JSON ===")
    loaded_data = load_rightmove_export_from_json(output_file)
    print("Load keys:", list(loaded_data.keys()))
    print("Loaded platform:", loaded_data.get("platform"))
    print("Loaded results count:", len(loaded_data.get("results", [])))
    print("Loaded cleaned_results count:", len(loaded_data.get("cleaned_results", [])))
    print("Loaded summary:", loaded_data.get("summary"))


def run_pagination_links_test(search_url: str, pages: int = 2) -> None:
    """Manual test: multi-page search → merged listing links."""
    print()
    print("=== Pagination listing links ===")
    links = extract_rightmove_listing_links_from_pages(search_url, pages)
    print("Pages:", pages)
    print("Total links count:", len(links))
    for link in links[:10]:
        print(link)


def run_multi_page_batch_test(search_url: str, pages: int = 2, limit: int = DEFAULT_BATCH_LIMIT) -> None:
    """Manual test: multi-page links + sequential listing scrapes."""
    print()
    print("=== Multi-page batch scrape ===")
    results = scrape_rightmove_search_results_from_pages(search_url, pages, limit)
    print("Pages:", pages)
    print("Limit:", limit)
    print("Multi-page batch results count:", len(results))
    for item in results:
        print("---")
        print("URL:", item.get("url"))
        print("Price:", item.get("price"))
        print("Address:", item.get("address"))
        print("Status:", item.get("status"))


def run_multi_page_export_test(
    search_url: str,
    pages: int = 2,
    limit: int = DEFAULT_BATCH_LIMIT,
    output_file: str = "rightmove_multi_page_export_test.json",
) -> None:
    """Manual test: multi-page export dict + save JSON."""
    print()
    print("=== Multi-page export / save ===")
    export_data = export_rightmove_results_from_pages(search_url, pages, limit)
    saved = save_rightmove_results_from_pages(search_url, output_file, pages, limit)
    print("Pages:", pages)
    print("Limit:", limit)
    print("Export keys:", list(export_data.keys()))
    print("Export summary:", export_data.get("summary"))
    print("Save success:", saved)
    print("Output file:", output_file)
    print("Cleaned results count:", len(export_data.get("cleaned_results", [])))


def run_multi_page_load_verify_test(file_path: str = "rightmove_multi_page_export_test.json") -> None:
    """Manual test: load multi-page export JSON + validate."""
    print()
    print("=== Multi-page load / verify ===")
    export_data = load_rightmove_results_from_pages_json(file_path)
    validation = validate_rightmove_export_data(export_data)
    print("File path:", file_path)
    print("Loaded keys:", list(export_data.keys()))
    print("Loaded cleaned_results count:", len(export_data.get("cleaned_results", [])))
    print("Loaded summary:", export_data.get("summary"))
    print("Validation result:", validation)


def run_rightmove_service_test(
    test_url: str,
    search_url: str,
    output_file: str = "rightmove_service_test.json",
) -> None:
    """Exercise run_rightmove_service for each supported mode."""
    print()
    print("=== SERVICE TEST: single ===")
    single_result = run_rightmove_service("single", test_url)
    print(single_result)

    print("=== SERVICE TEST: search_links ===")
    search_links_result = run_rightmove_service("search_links", search_url)
    print(search_links_result)

    print("=== SERVICE TEST: batch ===")
    batch_result = run_rightmove_service("batch", search_url, limit=3)
    print(batch_result)

    print("=== SERVICE TEST: multi_page_batch ===")
    multi_page_batch_result = run_rightmove_service("multi_page_batch", search_url, pages=2, limit=5)
    print(multi_page_batch_result)

    print("=== SERVICE TEST: export ===")
    export_result = run_rightmove_service("export", search_url, pages=2, limit=5)
    print(export_result)

    print("=== SERVICE TEST: save ===")
    save_result = run_rightmove_service("save", search_url, pages=2, limit=5, output_file=output_file)
    print(save_result)


def run_rightmove_payload_test(
    test_url: str,
    search_url: str,
    output_file: str = "rightmove_payload_test.json",
) -> None:
    """Exercise run_rightmove_service_from_payload with valid and invalid payloads."""
    print()
    single_payload = {"mode": "single", "url": test_url}
    print("=== PAYLOAD TEST: single ===")
    print(run_rightmove_service_from_payload(single_payload))

    batch_payload = {"mode": "batch", "url": search_url, "limit": 3}
    print("=== PAYLOAD TEST: batch ===")
    print(run_rightmove_service_from_payload(batch_payload))

    multi_payload = {"mode": "multi_page_batch", "url": search_url, "pages": 2, "limit": 5}
    print("=== PAYLOAD TEST: multi_page_batch ===")
    print(run_rightmove_service_from_payload(multi_payload))

    export_payload = {"mode": "export", "url": search_url, "pages": 2, "limit": 5}
    print("=== PAYLOAD TEST: export ===")
    print(run_rightmove_service_from_payload(export_payload))

    save_payload = {
        "mode": "save",
        "url": search_url,
        "pages": 2,
        "limit": 5,
        "output_file": output_file,
    }
    print("=== PAYLOAD TEST: save ===")
    print(run_rightmove_service_from_payload(save_payload))

    print("=== PAYLOAD TEST: invalid (not a dict) ===")
    print(run_rightmove_service_from_payload(None))

    print("=== PAYLOAD TEST: missing mode ===")
    print(run_rightmove_service_from_payload({"url": search_url}))

    print("=== PAYLOAD TEST: missing url ===")
    print(run_rightmove_service_from_payload({"mode": "single"}))


def run_rightmove_response_wrapper_test(
    test_url: str,
    search_url: str,
    output_file: str = "rightmove_response_test.json",
) -> None:
    """Smoke-test service/payload responses with build_rightmove_response envelope."""
    print()
    print("=== RESPONSE WRAPPER TEST: service single ===")
    print(run_rightmove_service("single", test_url))

    print("=== RESPONSE WRAPPER TEST: service batch ===")
    print(run_rightmove_service("batch", search_url, limit=3))

    print("=== RESPONSE WRAPPER TEST: service save ===")
    print(run_rightmove_service("save", search_url, pages=2, limit=3, output_file=output_file))

    print("=== RESPONSE WRAPPER TEST: payload single ===")
    single_payload = {
        "mode": "single",
        "url": test_url,
    }
    print(run_rightmove_service_from_payload(single_payload))

    print("=== RESPONSE WRAPPER TEST: payload invalid ===")
    print(run_rightmove_service_from_payload(None))


def run_rightmove_pipeline_test(
    test_url: str,
    search_url: str,
    output_file: str = "rightmove_pipeline_test.json",
) -> None:
    """Exercise execute_rightmove_pipeline with valid and invalid payloads."""
    print()
    print("=== PIPELINE TEST: single ===")
    single_payload = {"mode": "single", "url": test_url}
    print(execute_rightmove_pipeline(single_payload))

    print("=== PIPELINE TEST: batch ===")
    batch_payload = {"mode": "batch", "url": search_url, "limit": 3}
    print(execute_rightmove_pipeline(batch_payload))

    print("=== PIPELINE TEST: multi_page_batch ===")
    multi_payload = {"mode": "multi_page_batch", "url": search_url, "pages": 2, "limit": 5}
    print(execute_rightmove_pipeline(multi_payload))

    print("=== PIPELINE TEST: export ===")
    export_payload = {"mode": "export", "url": search_url, "pages": 2, "limit": 5}
    print(execute_rightmove_pipeline(export_payload))

    print("=== PIPELINE TEST: save ===")
    save_payload = {
        "mode": "save",
        "url": search_url,
        "pages": 2,
        "limit": 5,
        "output_file": output_file,
    }
    print(execute_rightmove_pipeline(save_payload))

    print("=== PIPELINE TEST: invalid (not a dict) ===")
    print(execute_rightmove_pipeline(None))

    print("=== PIPELINE TEST: missing mode ===")
    print(execute_rightmove_pipeline({"url": search_url}))

    print("=== PIPELINE TEST: missing url ===")
    print(execute_rightmove_pipeline({"mode": "single"}))


def run_rightmove_config_test() -> None:
    """Print key config constants (smoke-check Config Block v1)."""
    print()
    print("=== CONFIG (Config Block v1) ===")
    print("RIGHTMOVE_PLATFORM:", RIGHTMOVE_PLATFORM)
    print("DEFAULT_LIMIT:", DEFAULT_LIMIT)
    print("DEFAULT_PAGES:", DEFAULT_PAGES)
    print("DEFAULT_BATCH_LIMIT:", DEFAULT_BATCH_LIMIT)
    print("DEFAULT_TIMEOUT:", DEFAULT_TIMEOUT)
    print("DEFAULT_OUTPUT_FILE:", DEFAULT_OUTPUT_FILE)
    print("SUMMARY_CORE_FIELDS:", SUMMARY_CORE_FIELDS)
    print("DEFAULT_HEADERS keys:", list(DEFAULT_HEADERS.keys()))


def run_rightmove_input_validation_test() -> None:
    """Smoke-test input validation helpers (Part 22)."""
    print()
    print("=== INPUT VALIDATION (Part 22) ===")
    print("validate_rightmove_mode(single):", validate_rightmove_mode("single"))
    print("validate_rightmove_mode(xxx):", validate_rightmove_mode("xxx"))
    print(
        "validate_rightmove_url_input(valid):",
        validate_rightmove_url_input("https://www.rightmove.co.uk/properties/123"),
    )
    print("validate_rightmove_url_input(empty):", validate_rightmove_url_input(""))
    print("normalize_limit_input(3):", normalize_limit_input(3))
    print("normalize_limit_input(0):", normalize_limit_input(0))
    print("normalize_pages_input(2):", normalize_pages_input(2))
    print("normalize_pages_input(-1):", normalize_pages_input(-1))
    print("validate_output_file_input(test.json):", validate_output_file_input("test.json"))
    print("validate_output_file_input(empty):", validate_output_file_input(""))
    print("validate_rightmove_payload_input({}):", validate_rightmove_payload_input({}))
    print("validate_rightmove_payload_input(None):", validate_rightmove_payload_input(None))


def run_rightmove_mode_registry_test() -> None:
    """Print mode registry and helper outputs (Part 23)."""
    print()
    print("=== MODE REGISTRY (Part 23) ===")
    print("Supported modes:", build_rightmove_task_descriptor().get("supported_modes"))
    print("Description single:", get_rightmove_mode_description("single"))
    print("Description batch:", get_rightmove_mode_description("batch"))
    print("Description invalid:", get_rightmove_mode_description("xxx"))
    print("Validate single:", validate_rightmove_mode("single"))
    print("Validate invalid:", validate_rightmove_mode("xxx"))


def run_rightmove_task_descriptor_test() -> None:
    """Print task descriptor table and per-mode hints (Part 25)."""
    print()
    print("=== TASK DESCRIPTOR (Part 25) ===")
    print("Task descriptor:", build_rightmove_task_descriptor())
    print("Mode single:", get_rightmove_task_descriptor_by_mode("single"))
    print("Mode batch:", get_rightmove_task_descriptor_by_mode("batch"))
    print("Mode save:", get_rightmove_task_descriptor_by_mode("save"))
    print("Mode invalid:", get_rightmove_task_descriptor_by_mode("xxx"))


def run_rightmove_result_summary_test(test_url: str, search_url: str) -> None:
    """Exercise ``build_rightmove_result_summary`` / ``build_rightmove_response_with_summary``."""
    print()
    print("=== RESULT SUMMARY TEST: single ===")
    single_response = run_rightmove_service("single", test_url)
    print("Summary:", build_rightmove_result_summary(single_response))
    print("Enhanced:", build_rightmove_response_with_summary(single_response))

    print("=== RESULT SUMMARY TEST: batch ===")
    batch_response = run_rightmove_service("batch", search_url, limit=3)
    print("Summary:", build_rightmove_result_summary(batch_response))
    print("Enhanced:", build_rightmove_response_with_summary(batch_response))

    print("=== RESULT SUMMARY TEST: export ===")
    export_response = run_rightmove_service("export", search_url, pages=2, limit=3)
    print("Summary:", build_rightmove_result_summary(export_response))
    print("Enhanced:", build_rightmove_response_with_summary(export_response))

    print("=== RESULT SUMMARY TEST: invalid payload ===")
    invalid_response = run_rightmove_service_from_payload(None)
    print("Summary:", build_rightmove_result_summary(invalid_response))
    print("Enhanced:", build_rightmove_response_with_summary(invalid_response))


def run_rightmove_example_payloads_test(
    test_url: str,
    search_url: str,
    output_file: str = DEFAULT_OUTPUT_FILE,
) -> None:
    """Print example payload table and per-mode envelopes (Part 26)."""
    print()
    print("=== EXAMPLE PAYLOADS (Part 26) ===")
    print("All example payloads:", build_rightmove_example_payloads(test_url, search_url, output_file))
    print("Single example:", get_rightmove_example_payload_by_mode("single", test_url, search_url, output_file))
    print("Batch example:", get_rightmove_example_payload_by_mode("batch", test_url, search_url, output_file))
    print("Save example:", get_rightmove_example_payload_by_mode("save", test_url, search_url, output_file))
    print("Invalid example:", get_rightmove_example_payload_by_mode("xxx", test_url, search_url, output_file))


def run_rightmove_self_check_test() -> None:
    """Run and print module self-check (Part 27)."""
    print()
    print("=== SELF CHECK (Part 27) ===")
    run_rightmove_self_check()


def run_rightmove_capability_map_test() -> None:
    """Print capability map and sample lookups (Part 28)."""
    print()
    print("=== CAPABILITY MAP (Part 28) ===")
    print("Capability map:", build_rightmove_capability_map())
    print("Capability single_listing_parse:", get_rightmove_capability_status("single_listing_parse"))
    print("Capability batch_scrape_multi_page:", get_rightmove_capability_status("batch_scrape_multi_page"))
    print("Capability pipeline_entry:", get_rightmove_capability_status("pipeline_entry"))
    print("Capability invalid:", get_rightmove_capability_status("xxx"))


def run_rightmove_module_snapshot_test() -> None:
    """Print full module snapshot and section lookups (Part 29)."""
    print()
    print("=== MODULE SNAPSHOT (Part 29) ===")
    print("Module snapshot:", build_rightmove_module_snapshot())
    print("Snapshot supported_modes:", get_rightmove_snapshot_section("supported_modes"))
    print("Snapshot config:", get_rightmove_snapshot_section("config"))
    print("Snapshot capability_map:", get_rightmove_snapshot_section("capability_map"))
    print("Snapshot self_check:", get_rightmove_snapshot_section("self_check"))
    print("Snapshot invalid:", get_rightmove_snapshot_section("xxx"))


def run_rightmove_module_manifest_test() -> None:
    """Print module manifest and sample entry lookups (Part 30)."""
    print()
    print("=== MODULE MANIFEST (Part 30) ===")
    print("Module manifest:", build_rightmove_module_manifest())
    print("Manifest pipeline_entry:", get_rightmove_manifest_entry("pipeline_entry"))
    print("Manifest service_entry:", get_rightmove_manifest_entry("service_entry"))
    print("Manifest single_scrape:", get_rightmove_manifest_entry("single_scrape"))
    print("Manifest invalid:", get_rightmove_manifest_entry("xxx"))


def run_rightmove_final_check() -> None:
    """Print Phase 2 module status and readiness (Part 31)."""
    print()
    print("=== FINAL CHECK (Phase 2) ===")
    status = build_rightmove_module_status()
    print("Module status:", status)
    print("Is ready:", is_rightmove_module_ready())


if __name__ == "__main__":
    run_rightmove_config_test()
    run_rightmove_input_validation_test()
    run_rightmove_mode_registry_test()
    run_rightmove_task_descriptor_test()
    test_url = "https://www.rightmove.co.uk/properties/placeholder"
    search_url = (
        "https://www.rightmove.co.uk/property-to-rent/find.html?"
        "searchLocation=London&useLocationIdentifier=true&locationIdentifier=REGION%5E87490&radius=0.0"
    )
    output_file = DEFAULT_OUTPUT_FILE

    run_single_listing_test(test_url)
    run_search_links_test(search_url)
    run_pagination_links_test(search_url, pages=2)
    run_multi_page_batch_test(search_url, pages=2, limit=5)
    run_multi_page_export_test(
        search_url, pages=2, limit=5, output_file="rightmove_multi_page_export_test.json"
    )
    run_multi_page_load_verify_test("rightmove_multi_page_export_test.json")
    run_batch_test(search_url, limit=3)
    run_export_test(search_url, limit=3)
    run_save_load_test(search_url, limit=3, output_file=output_file)
    run_rightmove_service_test(
        test_url=test_url,
        search_url=search_url,
        output_file="rightmove_service_test.json",
    )
    run_rightmove_payload_test(
        test_url=test_url,
        search_url=search_url,
        output_file="rightmove_payload_test.json",
    )
    run_rightmove_response_wrapper_test(
        test_url=test_url,
        search_url=search_url,
        output_file="rightmove_response_test.json",
    )
    run_rightmove_pipeline_test(
        test_url=test_url,
        search_url=search_url,
        output_file="rightmove_pipeline_test.json",
    )
    run_rightmove_result_summary_test(test_url=test_url, search_url=search_url)
    run_rightmove_example_payloads_test(
        test_url=test_url,
        search_url=search_url,
        output_file=DEFAULT_OUTPUT_FILE,
    )
    run_rightmove_self_check_test()
    run_rightmove_capability_map_test()
    run_rightmove_module_snapshot_test()
    run_rightmove_module_manifest_test()
    run_rightmove_final_check()
