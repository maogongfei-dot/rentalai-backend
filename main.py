"""
RentalAI — Phase 1 Part 10: unified CLI / end-to-end chat demo.

Flow (single chain):
  user_text → handle_chat_request(user_text) → result → formatted print

Usage (from repo root):
  python main.py "Is my deposit protected?"
  python main.py
  python main.py --demo              # runs built-in E2E cases below
  python main.py --phase8            # UK location regression (uses same print layout)
  python main.py --phase9            # display regression (uses same print layout)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.chat import handle_chat_request

# ---------------------------------------------------------------------------
# Phase 1 Part 10 — Demo test inputs (contract / comparison / area / prefs / OOB)
# ---------------------------------------------------------------------------
DEMO_TEST_INPUTS: tuple[str, ...] = (
    "Is this deposit clause safe?",
    "Compare my current place in Manchester, £1100 bills included, with this property at M1 4BT",
    "M1 4BT",
    "I want something cheap and safe near the station",
    "I want to buy a house in London",
)

_PHASE9_DISPLAY_TESTS = (
    "Is this deposit clause risky?",
    "Compare my current place in Leeds with this property at B15 2TT",
    "Manchester M1 4BT",
    "I want something cheap and safe",
    "I want to buy a house in London",
)

_PHASE8_UK_LOCATION_TESTS = (
    "Manchester",
    "M1 4BT",
    "Manchester M1 4BT",
    "Affordable flat in Birmingham city centre",
    "Compare my current place in Leeds with this property at B15 2TT",
)

_DEFAULT_DETAIL = "No additional details available."
_PARTIAL = "Partial analysis only."


def _safe_str(value: Any, default: str = _DEFAULT_DETAIL) -> str:
    if value is None:
        return default
    s = str(value).strip()
    return s if s else default


def _format_followups(result: dict[str, Any]) -> str:
    lines: list[str] = []
    for item in result.get("followup_suggestions") or []:
        t = _safe_str(item, "")
        if t != _DEFAULT_DETAIL:
            lines.append(f"- {t}")
    nsp = _safe_str(result.get("next_step_prompt"), "")
    if nsp and nsp != _DEFAULT_DETAIL:
        lines.append(f"- {nsp}")
    if not lines:
        return _DEFAULT_DETAIL
    return "\n".join(lines)


def _format_preferences(result: dict[str, Any]) -> str:
    po = result.get("priority_order")
    order = ", ".join(str(x) for x in po) if isinstance(po, list) and po else ""
    raw_summary = result.get("user_signals_summary")
    summary = (str(raw_summary).strip() if raw_summary is not None else "") or ""

    parts: list[str] = []
    if order:
        parts.append(f"Priority order: {order}")
    if summary:
        parts.append(f"Summary: {summary}")
    if not parts:
        return _DEFAULT_DETAIL
    return "\n".join(parts)


def _format_analysis_route(result: dict[str, Any]) -> str:
    ar = result.get("analysis_route") or {}
    rt = _safe_str(ar.get("route_type"), _DEFAULT_DETAIL)
    reason = _safe_str(ar.get("route_reason"), "")
    conf = ar.get("route_confidence")
    line = f"route_type: {rt}"
    if reason and reason != _DEFAULT_DETAIL:
        line += f"\nroute_reason: {reason}"
    if conf is not None:
        line += f"\nroute_confidence: {conf}"
    return line


def _format_main_response(result: dict[str, Any]) -> str:
    dt = result.get("display_text")
    if isinstance(dt, str) and dt.strip():
        return dt.strip()
    rt = result.get("response_text")
    if isinstance(rt, str) and rt.strip():
        return f"{_PARTIAL}\n\n{rt.strip()}"
    return _PARTIAL


def _format_raw_debug(result: dict[str, Any]) -> str:
    """Compact structured snapshot for demos (not full JSON dumps)."""
    ar = result.get("analysis_route") or {}
    uk = result.get("uk_location_context") or {}
    pip = result.get("property_input_parsed") or {}
    comp = result.get("comparison_result")
    blob: dict[str, Any] = {
        "success": result.get("success"),
        "intent": result.get("intent"),
        "scope": result.get("scope"),
        "scope_handling": result.get("scope_handling"),
        "property_input_detected": result.get("property_input_detected"),
        "input_type": pip.get("input_type"),
        "analysis_route_type": ar.get("route_type"),
        "analysis_readiness": result.get("analysis_readiness"),
        "supports_uk_wide_routing": result.get("supports_uk_wide_routing"),
        "uk_location_type": uk.get("location_type"),
        "detected_cities": uk.get("detected_cities"),
        "detected_postcodes": uk.get("detected_postcodes"),
        "comparison_ready": (comp or {}).get("comparison_ready"),
        "source_module": result.get("source_module"),
    }
    return json.dumps(blob, indent=2, ensure_ascii=False)


def print_demo_result(result: dict[str, Any], user_text: str) -> None:
    """Unified console layout for debugging and demos."""
    city = _safe_str(result.get("city_context"), _DEFAULT_DETAIL)
    pc = _safe_str(result.get("postcode_context"), _DEFAULT_DETAIL)

    print("======== USER INPUT ========")
    print(user_text.strip() if user_text else _DEFAULT_DETAIL)

    print()
    print("======== INTENT / SCOPE ========")
    print(f"Intent: {_safe_str(result.get('intent'), _DEFAULT_DETAIL)}")
    print(f"Scope: {_safe_str(result.get('scope'), _DEFAULT_DETAIL)}")

    print()
    print("======== LOCATION CONTEXT ========")
    print(f"City: {city}")
    print(f"Postcode: {pc}")

    print()
    print("======== PREFERENCES ========")
    print(_format_preferences(result))

    print()
    print("======== ANALYSIS ROUTE ========")
    print(_format_analysis_route(result))

    print()
    print("======== MAIN RESPONSE ========")
    print(_format_main_response(result))

    print()
    print("======== FOLLOW UPS ========")
    print(_format_followups(result))

    print()
    print("======== RAW DEBUG (OPTIONAL) ========")
    print(_format_raw_debug(result))


def run_demo_batch(cases: tuple[str, ...], title: str) -> None:
    print(title)
    print()
    for i, text in enumerate(cases, 1):
        print()
        print("*" * 72)
        print(f"CASE {i}/{len(cases)}")
        print("*" * 72)
        try:
            result = handle_chat_request(text)
        except Exception as exc:
            print("======== USER INPUT ========")
            print(text)
            print()
            print(f"ERROR: {exc}")
            continue
        print_demo_result(result, text)


def main() -> None:
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    argv = sys.argv[1:]

    if argv and argv[0] in ("--demo", "--e2e", "--phase10"):
        run_demo_batch(DEMO_TEST_INPUTS, "RentalAI E2E Demo (Phase 1 Part 10)")
        return

    if argv and argv[0] in ("--phase9", "--display-tests"):
        run_demo_batch(_PHASE9_DISPLAY_TESTS, "Display layer regression (--phase9)")
        return

    if argv and argv[0] in ("--phase8", "--loc-tests", "--uk-location-tests"):
        run_demo_batch(_PHASE8_UK_LOCATION_TESTS, "UK location regression (--phase8)")
        return

    if argv:
        text = " ".join(argv)
    else:
        try:
            text = input("Enter message: ").strip()
        except EOFError:
            text = ""

    if not text:
        print("No input. Examples:")
        print('  python main.py "Is this deposit clause safe?"')
        print("  python main.py --demo")
        return

    try:
        result = handle_chat_request(text)
    except Exception as exc:
        print("======== USER INPUT ========")
        print(text)
        print()
        print(f"ERROR: {exc}")
        return

    print_demo_result(result, text)


if __name__ == "__main__":
    main()
