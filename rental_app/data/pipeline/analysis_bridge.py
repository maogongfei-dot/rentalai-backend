# P7 Phase4：多平台归一结果 → analyze-batch 桥接（不改评分引擎、不改 ListingSchema 核心）
from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

_perf_log = logging.getLogger("rentalai.perf")

from api_analysis import analyze_batch_request_body
from data.normalizer.listing_normalizer import to_analyze_payload
from data.pipeline.multi_source_pipeline import run_multi_source_pipeline
from data.schema.listing_schema import ListingSchema

_DEBUG_DIR = Path(__file__).resolve().parent.parent / "scraper" / "samples" / "debug"


def _to_float_simple(v: Any) -> float | None:
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        s = v.strip().replace(",", "")
        if not s:
            return None
        try:
            return float(s)
        except ValueError:
            return None
    return None


def _to_int_simple(v: Any) -> int | None:
    f = _to_float_simple(v)
    if f is None:
        return None
    if abs(f - round(f)) < 1e-9:
        return int(round(f))
    return int(f)


def _clean_lower(s: Any) -> str:
    if s is None:
        return ""
    t = str(s).strip().lower()
    return t


def _listing_property_category(listing_pt: Any) -> str | None:
    a = _clean_lower(listing_pt)
    if not a:
        return None
    if "studio" in a:
        return "studio"
    if any(x in a for x in ("flat", "apartment", "apt", "maisonette")):
        return "flat"
    if any(
        x in a
        for x in (
            "house",
            "bungalow",
            "detached",
            "semi-detached",
            "semi detached",
            "terraced",
            "terrace",
            "cottage",
            "town house",
            "townhouse",
        )
    ):
        return "house"
    return None


def _wanted_property_category(want_raw: Any) -> str | None:
    w = _clean_lower(want_raw)
    if not w or w == "other":
        return None
    if w == "apartment":
        w = "flat"
    if w in ("flat", "house", "studio"):
        return w
    return None


def _listing_matches_property_type(listing: dict[str, Any], want_raw: Any) -> bool:
    want = _wanted_property_category(want_raw)
    if want is None:
        return True
    lcat = _listing_property_category(listing.get("property_type"))
    if lcat is None:
        return True
    return lcat == want


def _listing_matches_bedrooms(listing: dict[str, Any], bedrooms_pref: Any) -> bool:
    if bedrooms_pref is None:
        return True
    sp = str(bedrooms_pref).strip().upper()
    if not sp:
        return True
    lb = _to_int_simple(listing.get("bedrooms"))
    if lb is None:
        return True
    if sp == "4+":
        return lb >= 4
    try:
        need = int(float(sp))
    except ValueError:
        return True
    return lb == need


def _listing_matches_bathrooms(listing: dict[str, Any], min_bath: Any) -> bool:
    need = _to_float_simple(min_bath)
    if need is None:
        return True
    lb = _to_float_simple(listing.get("bathrooms"))
    if lb is None:
        return True
    return lb + 1e-6 >= need


def _listing_matches_distance(listing: dict[str, Any], dist_pref: Any) -> bool:
    key = _clean_lower(dist_pref)
    if not key or key == "any":
        return True
    max_miles = {"1": 1.0, "3": 3.0, "5": 5.0}.get(key)
    if max_miles is None:
        return True
    dm = _to_float_simple(listing.get("distance_miles"))
    if dm is None:
        dm = _to_float_simple(listing.get("target_postcode_distance_miles"))
    if dm is None:
        return True
    return dm <= max_miles + 0.05


def _listing_matches_prefs_row(listing: dict[str, Any], prefs: dict[str, Any]) -> bool:
    if not isinstance(listing, dict):
        return False
    if not _listing_matches_property_type(listing, prefs.get("property_type")):
        return False
    if not _listing_matches_bedrooms(listing, prefs.get("bedrooms")):
        return False
    if not _listing_matches_bathrooms(listing, prefs.get("bathrooms")):
        return False
    if not _listing_matches_distance(listing, prefs.get("distance_to_centre")):
        return False
    return True


def filter_aggregated_listings_by_preferences(
    listings: list[dict[str, Any]],
    prefs: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    """Soft filter before batch analyze; if nothing matches, returns the original list."""
    if not listings:
        return listings
    if not prefs or not isinstance(prefs, dict):
        return listings
    has_any = any(
        prefs.get(k) not in (None, "", "any")
        for k in ("property_type", "bedrooms", "bathrooms", "distance_to_centre", "safety_preference")
    )
    if not has_any:
        return listings
    filtered = [d for d in listings if isinstance(d, dict) and _listing_matches_prefs_row(d, prefs)]
    if not filtered:
        return listings
    return filtered
_ANALYSIS_SAMPLE_PATH = _DEBUG_DIR / "multi_source_analysis_sample.json"


def listing_schema_dict_to_batch_property(
    row: dict[str, Any],
    *,
    budget: float | None = None,
    target_postcode: str | None = None,
) -> dict[str, Any]:
    """单条归一 listing dict → analyze-batch `properties[]` 单元素（复用 to_analyze_payload）。"""
    listing = ListingSchema.from_dict(row if isinstance(row, dict) else {})
    return to_analyze_payload(listing, budget=budget, target_postcode=target_postcode)


def listings_dicts_to_batch_properties(
    rows: list[dict[str, Any]],
    *,
    budget: float | None = None,
    target_postcode: str | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """`(properties, conversion_errors)`；单行映射失败记入 errors，不中断整批。"""
    props: list[dict[str, Any]] = []
    errs: list[dict[str, Any]] = []
    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            errs.append({"row_index": i, "error": "row is not a dict"})
            continue
        try:
            p = listing_schema_dict_to_batch_property(
                row,
                budget=budget,
                target_postcode=target_postcode,
            )
            if not p:
                errs.append({"row_index": i, "error": "empty analyze payload after mapping"})
                continue
            props.append(p)
        except Exception as e:  # noqa: BLE001
            errs.append({"row_index": i, "error": f"{type(e).__name__}: {e}"})
    return props, errs


def listings_to_batch_analysis_payload(
    rows: list[dict[str, Any]],
    *,
    budget: float | None = None,
    target_postcode: str | None = None,
) -> list[dict[str, Any]]:
    """仅返回 `properties` 列表，便于与手工组装的 batch body 合并。"""
    props, _ = listings_dicts_to_batch_properties(
        rows,
        budget=budget,
        target_postcode=target_postcode,
    )
    return props


def fetch_multi_source_listings(
    *,
    sources: list[str] | None = None,
    query: dict[str, Any] | None = None,
    limit_per_source: int = 20,
    persist: bool = True,
    storage_path: str | None = None,
    save_aggregated_sample: bool = False,
) -> dict[str, Any]:
    """仅抓取聚合；`aggregated_listings` 为去重后的 listing dict 列表。"""
    return run_multi_source_pipeline(
        sources=sources,
        query=query,
        limit_per_source=limit_per_source,
        persist=persist,
        storage_path=storage_path,
        save_aggregated_sample=save_aggregated_sample,
        include_aggregated_listings=True,
    )


def analyze_multi_source_listings(
    aggregated_listings: list[dict[str, Any]],
    *,
    budget: float | None = None,
    target_postcode: str | None = None,
) -> dict[str, Any]:
    """
    已聚合的 listing dicts → `analyze_batch_request_body`。
    映射后若无有效 property，返回 `success: False` 与结构化 error，不抛异常。
    """
    props, conv_errs = listings_dicts_to_batch_properties(
        aggregated_listings,
        budget=budget,
        target_postcode=target_postcode,
    )
    if not props:
        return {
            "success": False,
            "error": {
                "message": "No valid properties for batch analysis after ListingSchema mapping",
                "type": "bridge_error",
                "details": {
                    "conversion_errors": conv_errs,
                    "aggregated_count": len(aggregated_listings),
                },
            },
            "analyze_envelope": None,
            "conversion_errors": conv_errs,
            "properties_built_count": 0,
        }
    envelope = analyze_batch_request_body({"properties": props})
    return {
        "success": bool(envelope.get("success")),
        "error": envelope.get("error"),
        "analyze_envelope": envelope,
        "conversion_errors": conv_errs,
        "properties_built_count": len(props),
    }


def _pipeline_compact(pl: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in pl.items() if k != "aggregated_listings"}


def _first_success_batch_row(results: Any) -> dict[str, Any] | None:
    if not isinstance(results, list):
        return None
    for r in results:
        if isinstance(r, dict) and r.get("success"):
            return r
    return None


def _maybe_write_analysis_sample(payload: dict[str, Any], *, enabled: bool) -> None:
    if not enabled:
        return
    try:
        _ANALYSIS_SAMPLE_PATH.parent.mkdir(parents=True, exist_ok=True)
        _ANALYSIS_SAMPLE_PATH.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
    except (OSError, TypeError, ValueError):
        pass


def run_multi_source_analysis(
    *,
    sources: list[str] | None = None,
    query: dict[str, Any] | None = None,
    limit_per_source: int = 20,
    persist: bool = True,
    storage_path: str | None = None,
    save_aggregated_sample: bool = False,
    save_analysis_sample: bool = False,
    budget: float | None = None,
    target_postcode: str | None = None,
    user_preferences: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    `run_multi_source_pipeline` → 去重 listing dicts → `analyze_batch_request_body`。
    子 pipeline 部分失败时仍可能对已成功平台的 listings 做 batch 分析。
    """
    _t_total = time.perf_counter()
    if limit_per_source <= 0:
        return {
            "success": False,
            "pipeline_success": False,
            "sources_run": [],
            "errors": [{"stage": "validation", "error": "limit_per_source must be > 0"}],
            "total_analyzed_count": 0,
            "analysis_envelope": None,
        }
    errors: list[dict[str, Any]] = []
    q = dict(query or {})
    save_dbg = bool(save_analysis_sample) or bool(q.pop("save_analysis_sample", False))

    _t_pipeline = time.perf_counter()
    pl = run_multi_source_pipeline(
        sources=sources,
        query=q,
        limit_per_source=limit_per_source,
        persist=persist,
        storage_path=storage_path,
        save_aggregated_sample=save_aggregated_sample,
        include_aggregated_listings=True,
    )

    _perf_log.info("[PERF] scraper pipeline took %.3fs", time.perf_counter() - _t_pipeline)

    for e in pl.get("errors") or []:
        if isinstance(e, dict):
            row = {"stage": "multi_source_pipeline", **e}
        else:
            row = {"stage": "multi_source_pipeline", "error": str(e)}
        errors.append(row)

    listings = pl.get("aggregated_listings") or []
    ux_prefs = user_preferences if isinstance(user_preferences, dict) else None
    listings_for_batch = filter_aggregated_listings_by_preferences(listings, ux_prefs)
    _t_analysis = time.perf_counter()
    analysis_block = analyze_multi_source_listings(
        listings_for_batch,
        budget=budget,
        target_postcode=target_postcode,
    )
    _perf_log.info("[PERF] batch analysis of %d listings took %.3fs", len(listings), time.perf_counter() - _t_analysis)

    for ce in analysis_block.get("conversion_errors") or []:
        if isinstance(ce, dict):
            errors.append({"stage": "listing_to_analyze_payload", **ce})
        else:
            errors.append({"stage": "listing_to_analyze_payload", "error": ce})

    if not analysis_block.get("success"):
        err = analysis_block.get("error")
        if err:
            errors.append({"stage": "analyze_batch", "error": err})

    env = analysis_block.get("analyze_envelope") or {}
    data = env.get("data") if isinstance(env, dict) else None
    data = data if isinstance(data, dict) else {}
    meta = env.get("meta") if isinstance(env, dict) else None
    meta = meta if isinstance(meta, dict) else {}
    batch_summary = meta.get("batch_summary") if isinstance(meta.get("batch_summary"), dict) else {}

    props_built = int(analysis_block.get("properties_built_count") or 0)
    overall_ok = bool(analysis_block.get("success")) and props_built > 0

    pipeline_ok = pl.get("success") is True
    degraded = overall_ok and not pipeline_ok
    if degraded:
        _perf_log.warning("[DEGRADED] analysis succeeded with partial pipeline failure")

    out: dict[str, Any] = {
        "success": overall_ok,
        "degraded": degraded,
        "pipeline_success": pl.get("success"),
        "sources_run": pl.get("sources_run") or [],
        "total_raw_count": pl.get("total_raw_count"),
        "total_normalized_count": pl.get("total_normalized_count"),
        "aggregated_unique_count": pl.get("aggregated_unique_count"),
        "total_analyzed_count": batch_summary.get("requested", props_built),
        "batch_succeeded": batch_summary.get("succeeded"),
        "batch_failed": batch_summary.get("failed"),
        "properties_built_count": props_built,
        "total_saved": pl.get("total_saved"),
        "total_updated": pl.get("total_updated"),
        "total_skipped": pl.get("total_skipped"),
        "pipeline": _pipeline_compact(pl),
        "analysis_summary": data.get("comparison_summary"),
        "top_recommendations": data.get("top_recommendation"),
        "sample_analyzed_listing": _first_success_batch_row(data.get("results")),
        "analysis_envelope": env if env else None,
        "errors": errors,
        "user_preferences": dict(ux_prefs) if ux_prefs else {},
    }

    _maybe_write_analysis_sample(
        {
            "pipeline": out["pipeline"],
            "stats": {
                "sources_run": out["sources_run"],
                "total_raw_count": out["total_raw_count"],
                "total_normalized_count": out["total_normalized_count"],
                "aggregated_unique_count": out["aggregated_unique_count"],
                "total_analyzed_count": out["total_analyzed_count"],
                "batch_succeeded": out["batch_succeeded"],
                "batch_failed": out["batch_failed"],
            },
            "analysis_summary": out["analysis_summary"],
            "top_1": data.get("top_1_recommendation"),
            "sample_analyzed_listing": out["sample_analyzed_listing"],
        },
        enabled=save_dbg,
    )

    _perf_log.info("[PERF] run_multi_source_analysis total %.3fs", time.perf_counter() - _t_total)
    return out
