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
  python main.py --contract          # Phase 3: contract mode (shortcut for --mode contract)
  python main.py --mode contract     # explicit contract analysis mode
  python main.py --mode property "…" # explicit property / chat analysis (handle_chat_request)
  python main.py --auto-test         # Phase 3: rule-based intent detection (contract vs property)
  python main.py --contract-norm-test  # Phase 3: contract input normalizer smoke (two samples)
  python main.py --contract-actions-test  # Phase 3: action suggestions + synthetic failure envelope
  python main.py --missing-clause-test    # Phase 3: missing clause checker (sparse vs full text)
  python main.py --flagged-clause-test    # Phase 3: risk sentence locator (flagged segments)
  python main.py --verdict-test           # Phase 3: final verdict (high vs low+incomplete)
  python main.py --contract-demo          # Phase 3: standalone contract analysis demo (two samples)
  python main.py --contract-batch-test    # Phase 3: contract_test_runner (batch + assertions)
  python main.py --contract-urgency-test  # Phase 4 Part 9: urgency & priority (demo + assertions)
  python main.py --contract-decision-factors-test  # Phase 4 Part 10: supporting / blocking factors
"""

from __future__ import annotations

import json
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.chat import handle_chat_request
from modules.contract.contract_handler import handle_contract_input
from modules.contract.contract_presenter import print_contract_result as print_contract_user_facing
from utils.system_logger import log_system_result
from modules.contract.contract_service import (
    build_contract_result,
    build_contract_verdict,
    contract_normalized_text,
    detect_missing_contract_clauses,
    extract_flagged_clauses,
    print_contract_result as print_contract_formatted_appendix,
)
from modules.actions.action_engine import build_next_actions
from modules.followup.followup_engine import build_followup_questions
from modules.output.response_formatter import build_final_response_text

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

# Phase 3 Part 8 — CLI analysis mode (property = chat/property pipeline; contract = contract_handler)
MODE_PROPERTY = "property"
MODE_CONTRACT = "contract"
_DEFAULT_CONTRACT_SAMPLE = (
    "The landlord may increase rent with notice. "
    "The tenant must pay a non-refundable fee."
)

# Phase 3 Part 9 — rule-based intent (no LLM)
_CONTRACT_INTENT_KEYWORDS: tuple[str, ...] = (
    "contract",
    "agreement",
    "clause",
    "tenant",
    "landlord",
    "deposit",
    "rent increase",
    "legal",
)
_CONTRACT_INTENT_LONG_TEXT_LEN = 200

# Phase 3 Part 27–28 — last routed pipeline outcome (unified shell from ``build_system_result``)
system_result: dict[str, Any] | None = None


def _merge_final_display_meta(system_result: dict[str, Any]) -> None:
    """Fill ``result.final_display.meta_block`` from the outer shell (Phase 4 Part 5)."""
    if not isinstance(system_result, dict):
        return
    inner = system_result.get("result")
    if not isinstance(inner, dict):
        return
    fd = inner.get("final_display")
    if not isinstance(fd, dict):
        return
    meta = fd.get("meta_block")
    if not isinstance(meta, dict):
        meta = {}
    meta["source"] = str(system_result.get("source") or "")
    meta["request_id"] = str(system_result.get("request_id") or "")
    meta["timestamp"] = str(system_result.get("timestamp") or "")
    fd["meta_block"] = meta


def build_system_result(
    module_name: str, result: dict[str, Any], source: str = "unknown"
) -> dict[str, Any]:
    """
    Wrap a module-specific result dict for the main system (UI / API / history hooks).

    Inner ``result`` is unchanged; this layer only adds a stable outer shape.
    ``source`` tags how the input reached the main flow (Phase 3 Part 33).
    ``request_id`` / ``timestamp`` are fresh on each call (Phase 3 Part 34).
    """
    request_id = str(uuid.uuid4())
    timestamp = datetime.utcnow().isoformat()
    return {
        "ok": result.get("ok"),
        "module": module_name,
        "source": source,
        "request_id": request_id,
        "timestamp": timestamp,
        "result": result,
        "error": result.get("error"),
    }


def detect_intent(user_input: str) -> str:
    """
    Return ``MODE_CONTRACT`` or ``MODE_PROPERTY`` using simple keyword / length rules.
    """
    s = str(user_input) if not isinstance(user_input, str) else user_input
    if len(s) > _CONTRACT_INTENT_LONG_TEXT_LEN:
        return MODE_CONTRACT
    low = s.lower()
    for kw in _CONTRACT_INTENT_KEYWORDS:
        if kw in low:
            return MODE_CONTRACT
    return MODE_PROPERTY


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

def _format_product_output(result: dict[str, Any]) -> str:
    product_output = result.get("product_output") or {}
    if not isinstance(product_output, dict) or not product_output:
        return _DEFAULT_DETAIL
    return json.dumps(product_output, indent=2, ensure_ascii=False)


def _print_explain_result_block(result: dict[str, Any]) -> None:
    """Print modules.explain-shaped ``explain_result`` when present (summary / pros / cons / recommendation)."""
    er = result.get("explain_result")
    if not isinstance(er, dict):
        return
    print()
    print("【Explain Summary】")
    summary = er.get("summary")
    print("" if summary is None else str(summary).strip())
    print()
    print("【Pros】")
    pros = er.get("pros")
    if isinstance(pros, list):
        for item in pros:
            text = str(item).strip() if item is not None else ""
            if text:
                print(f"- {text}")
    print()
    print("【Cons】")
    cons = er.get("cons")
    if isinstance(cons, list):
        for item in cons:
            text = str(item).strip() if item is not None else ""
            if text:
                print(f"- {text}")
    print()
    print("【Recommendation】")
    rec = er.get("recommendation")
    print("" if rec is None else str(rec).strip())


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

    decision = result.get("decision") or {}
    if isinstance(decision, dict) and decision:
        print()
        print("======== DECISION ========")
        print(f"Status: {_safe_str(decision.get('decision_status'), _DEFAULT_DETAIL)}")
        print(f"Title: {_safe_str(decision.get('decision_title'), _DEFAULT_DETAIL)}")
        print(f"Summary: {_safe_str(decision.get('decision_summary'), _DEFAULT_DETAIL)}")
        print(f"Action: {_safe_str(decision.get('decision_action'), _DEFAULT_DETAIL)}")

    final_result = {
        "explain_result": result.get("explain_result"),
        "summary": result.get("summary") or result.get("response_text") or result.get("display_text"),
        "recommendation": (decision.get("decision_action") if isinstance(decision, dict) else None),
        "risks": ((result.get("risk_result") or {}).get("risk_markers") if isinstance(result.get("risk_result"), dict) else []),
        "reasons": ((result.get("explanation_summary") or {}).get("key_positives") if isinstance(result.get("explanation_summary"), dict) else []),
    }
    po = result.get("product_output")
    api_next = po.get("next_actions") if isinstance(po, dict) else None
    if isinstance(api_next, list) and api_next:
        final_result["next_actions"] = api_next
    else:
        final_result["next_actions"] = build_next_actions(final_result)
    final_result["followup_questions"] = build_followup_questions(final_result)
    formatted_response = build_final_response_text(final_result)

    print()
    print("======== MAIN RESPONSE ========")
    if formatted_response:
        print(formatted_response)
        print()
        print("======== FINAL RESPONSE ========")
        print(formatted_response)
    else:
        print(_format_main_response(result))

    print()
    print("======== FOLLOW UPS ========")
    print(_format_followups(result))

    print()
    print("======== PRODUCT OUTPUT ========")
    print(_format_product_output(result))

    _print_explain_result_block(result)

    print()
    print("======== RAW DEBUG (OPTIONAL) ========")
    print(_format_raw_debug(result))

def run_contract_pipeline_for_text(
    text: str, *, show_mode_banner: bool = True, source: str = "unknown"
) -> None:
    """Contract mode: CLI framing + ``handle_contract_input`` + formatted appendix."""
    global system_result
    normalized = contract_normalized_text(text)
    if show_mode_banner:
        print("======== ANALYSIS MODE: contract ========")
    print("Normalized contract text:", normalized[:200])
    print("======== CONTRACT INPUT ========")
    print(normalized if normalized else _DEFAULT_DETAIL)
    print()
    contract_result = handle_contract_input(text, print_result=False)
    system_result = build_system_result("contract", contract_result, source=source)
    _merge_final_display_meta(system_result)
    print()
    print_contract_user_facing(system_result["result"])
    print()
    # Technical appendix (risk counts / per-clause; not the unified user block)
    print_contract_formatted_appendix(
        {
            "ok": contract_result.get("ok"),
            "summary": contract_result.get("summary"),
            "details": contract_result.get("details"),
            "error": contract_result.get("error"),
        }
    )


from modules.contract.contract_test_runner import (
    run_contract_batch_test,
    run_contract_completeness_test,
    run_contract_confidence_test,
    run_contract_decision_factors_test,
    run_contract_demo,
    run_contract_direct_answer_test,
    run_contract_final_display_test,
    run_contract_human_output_test,
    run_contract_urgency_test,
)


def run_contract_integration_test() -> None:
    """Phase 3 — smoke test: contract mode with built-in sample text."""
    run_contract_pipeline_for_text(_DEFAULT_CONTRACT_SAMPLE)


def run_property_pipeline_for_text(
    text: str, *, show_mode_banner: bool = True, source: str = "unknown"
) -> None:
    """Property mode: existing chat / property analysis (unchanged behaviour)."""
    global system_result
    if show_mode_banner:
        print("======== ANALYSIS MODE: property ========")
    try:
        property_result = handle_chat_request(text)
    except Exception as exc:
        system_result = build_system_result(
            "property", {"ok": False, "error": str(exc)}, source=source
        )
        print("======== USER INPUT ========")
        print(text)
        print()
        print(f"ERROR: {exc}")
        return
    system_result = build_system_result("property", property_result, source=source)
    print_demo_result(property_result, text)


def run_main_flow(user_input: str, source: str = "unknown") -> dict[str, Any]:
    """
    Unified entry: intent detection → contract or property pipeline → unified ``system_result``.

    Reuses ``run_contract_pipeline_for_text`` / ``run_property_pipeline_for_text`` so CLI output
    and handler/presenter behaviour stay unchanged (Phase 3 Part 29).
    """
    global system_result
    intent = detect_intent(user_input)
    print("Detected mode:", intent)
    if intent == MODE_CONTRACT:
        run_contract_pipeline_for_text(user_input, show_mode_banner=False, source=source)
    else:
        run_property_pipeline_for_text(user_input, show_mode_banner=False, source=source)
    if system_result is None:
        sr = build_system_result(
            "property", {"ok": False, "error": "no system result"}, source=source
        )
        log_system_result(sr)
        return sr
    log_system_result(system_result)
    return system_result


def run_auto_routed_pipeline(text: str) -> None:
    """Phase 3 Part 9 / 29: thin wrapper around ``run_main_flow`` (legacy name)."""
    run_main_flow(text)


def run_contract_actions_smoke_test() -> None:
    """Phase 3 Part 12: synthetic failure envelope; use ``python main.py --contract`` for live high-risk actions."""
    print("=== Part 12: actions (failure envelope) ===\n")
    fo = build_contract_result({"ok": False, "error": "Synthetic test error"}, "")
    print("Module:", fo["module"])
    print("OK:", fo["ok"])
    print("Error:", fo.get("error"))
    print("Actions:")
    for a in fo["actions"]:
        print("-", a)
    print("Missing clauses:")
    for item in fo.get("missing_clauses") or []:
        print("-", item)
    print("Flagged clauses:")
    for item in fo.get("flagged_clauses") or []:
        print("-", item)
    v = fo.get("verdict") or {}
    print("Verdict:", v.get("status"), "|", v.get("title"))


def run_verdict_smoke_test() -> None:
    """Part 15: synthetic final_output shapes — high_risk vs review_needed (low + gaps)."""
    high = {
        "ok": True,
        "summary": {"risk_level": "high"},
        "missing_clauses": [],
        "flagged_clauses": [],
    }
    low_gaps = {
        "ok": True,
        "summary": {"risk_level": "low"},
        "missing_clauses": ["a", "b", "c"],
        "flagged_clauses": [],
    }
    print("=== Part 15: high risk verdict ===\n", build_contract_verdict(high))
    print("\n=== Part 15: low risk + 3 missing (review_needed) ===\n", build_contract_verdict(low_gaps))


def run_flagged_clause_smoke_test() -> None:
    """Part 14: high-signal text vs calmer text."""
    risky = (
        "The tenant must pay a non-refundable fee. "
        "The landlord may terminate the agreement immediately."
    )
    calm = "The property is at 1 Example Street. The tenancy starts on 1 June."
    print("=== Part 14: risky sample (expect flagged segments) ===\n")
    print(extract_flagged_clauses(contract_normalized_text(risky)))
    print("\n=== Part 14: calmer sample (expect few or none) ===\n")
    print(extract_flagged_clauses(contract_normalized_text(calm)))


def run_missing_clause_smoke_test() -> None:
    """Part 13: sparse vs fuller contract text — missing list should shrink."""
    sparse = "The landlord may increase rent with notice."
    full = (
        "Rent is £1000 monthly. Deposit £800. Notice period 2 months. "
        "Termination and end of tenancy. Repair and maintenance. Admin fee £50."
    )
    print("=== Part 13: sparse text (expect several gaps) ===\n")
    print(detect_missing_contract_clauses(contract_normalized_text(sparse)))
    print("\n=== Part 13: fuller text (expect fewer or none) ===\n")
    print(detect_missing_contract_clauses(contract_normalized_text(full)))


def run_contract_normalizer_smoke_test() -> None:
    """Phase 3 Part 10: short clause + messy whitespace; both should route as contract."""
    cases = (
        "The landlord may increase rent with notice.",
        "The landlord    may increase rent.\n\nThe tenant must pay deposit.",
    )
    print("=== Contract normalizer smoke test (Part 10) ===\n")
    for raw in cases:
        print("*" * 72)
        print("Detected mode:", detect_intent(raw))
        run_contract_pipeline_for_text(raw, show_mode_banner=False)
        print()


def run_intent_auto_test() -> None:
    """Two samples: contract-like keywords vs short property query."""
    contract_like = (
        "This tenancy agreement sets the deposit at £800. "
        "The landlord may give notice under the contract clause."
    )
    property_like = "Cheap 2-bed flat M1 4BT near station"
    print("=== Intent auto-test (Part 9) ===\n")
    for label, sample in (("contract sample", contract_like), ("property sample", property_like)):
        print("*" * 72)
        print(label + ":")
        print(sample[:120] + ("..." if len(sample) > 120 else ""))
        intent = detect_intent(sample)
        print("Detected mode:", intent)
        print()


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


def launch_main(user_input: str | None = None) -> dict[str, Any]:
    """
    Process entrypoint (Phase 3 Part 30–33).

    - With CLI arguments, delegates to ``main()`` and returns ``system_result`` when set.
    - With explicit ``user_input``, runs ``run_main_flow`` with ``source="direct_input"``.
    - With no arguments and no ``user_input``, multiline input (``END``) then ``source="cli_multiline"``.
    """
    argv = sys.argv[1:]

    if user_input is not None:
        if sys.platform == "win32":
            try:
                sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass
        sr = run_main_flow(user_input, source="direct_input")
        print("Launcher source:", sr.get("source"))
        print("Launcher module:", sr.get("module"))
        print("Launcher ok:", sr.get("ok"))
        return sr

    if argv:
        main()
        return (
            system_result
            if system_result is not None
            else build_system_result(
                "property", {"ok": False, "error": "no system result"}, source="unknown"
            )
        )

    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    print("Enter your text for analysis.")
    print("You can paste multiple lines.")
    print("Type END on a new line to finish input.")
    print("- Paste a contract clause or tenancy text for contract analysis")
    print("- Or enter a property/rental description for property analysis")
    lines: list[str] = []
    while True:
        try:
            line = input()
        except EOFError:
            break
        if line.strip() == "END":
            break
        lines.append(line)
    interactive_input = "\n".join(lines).strip()
    if not interactive_input:
        print("Empty input received.")
    sr = run_main_flow(interactive_input, source="cli_multiline")
    print("Launcher source:", sr.get("source"))
    print("Launcher module:", sr.get("module"))
    print("Launcher ok:", sr.get("ok"))
    return sr


def main() -> None:
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    argv = sys.argv[1:]

    if argv and argv[0] in ("--demo", "--e2e"):
        run_demo_batch(DEMO_TEST_INPUTS, "RentalAI E2E Demo (Phase 1 Part 10)")
        return

    if argv and argv[0] in ("--phase9", "--display-tests"):
        run_demo_batch(_PHASE9_DISPLAY_TESTS, "Phase 9 decision/display regression (--phase9)")
        return 

    if argv and argv[0] in ("--phase10", "--product-output-tests"):
        run_demo_batch(_PHASE9_DISPLAY_TESTS, "Phase 10 product output regression (--phase10)")
        return

    if argv and argv[0] in ("--phase8", "--loc-tests", "--uk-location-tests"):
        run_demo_batch(_PHASE8_UK_LOCATION_TESTS, "UK location regression (--phase8)")
        return

    if argv and argv[0] in ("--auto-test", "--intent-test", "--phase3-intent"):
        run_intent_auto_test()
        return

    if argv and argv[0] in ("--contract-norm-test", "--phase3-part10"):
        run_contract_normalizer_smoke_test()
        return

    if argv and argv[0] in ("--contract-actions-test", "--phase3-part12"):
        run_contract_actions_smoke_test()
        return

    if argv and argv[0] in ("--missing-clause-test", "--phase3-part13"):
        run_missing_clause_smoke_test()
        return

    if argv and argv[0] in ("--flagged-clause-test", "--phase3-part14"):
        run_flagged_clause_smoke_test()
        return

    if argv and argv[0] in ("--verdict-test", "--phase3-part15"):
        run_verdict_smoke_test()
        return

    if argv and argv[0] in ("--contract-demo", "--phase3-part17"):
        run_contract_demo()
        return

    if argv and argv[0] in ("--contract-batch-test", "--phase3-part18"):
        run_contract_batch_test()
        return

    if argv and argv[0] in ("--contract-human-test", "--phase4-part4"):
        run_contract_human_output_test()
        return

    if argv and argv[0] in ("--contract-final-display-test", "--phase4-part5"):
        run_contract_final_display_test()
        return

    if argv and argv[0] in ("--contract-completeness-test", "--phase4-part6"):
        run_contract_completeness_test()
        return

    if argv and argv[0] in ("--contract-direct-answer-test", "--phase4-part7"):
        run_contract_direct_answer_test()
        return

    if argv and argv[0] in ("--contract-confidence-test", "--phase4-part8"):
        run_contract_confidence_test()
        return

    if argv and argv[0] in ("--contract-urgency-test", "--phase4-part9"):
        run_contract_urgency_test()
        return

    if argv and argv[0] in ("--contract-decision-factors-test", "--phase4-part10"):
        run_contract_decision_factors_test()
        return

    if argv and argv[0] == "--mode":
        if len(argv) < 2:
            print("Usage: python main.py --mode contract [optional contract text...]")
            print("       python main.py --mode property [optional message...]")
            return
        mode = argv[1].lower()
        rest = argv[2:]
        if mode == MODE_CONTRACT:
            text = " ".join(rest).strip() if rest else _DEFAULT_CONTRACT_SAMPLE
            run_contract_pipeline_for_text(text)
            return
        if mode == MODE_PROPERTY:
            text = " ".join(rest).strip() if rest else ""
            if not text:
                try:
                    text = input("Enter message (property mode): ").strip()
                except EOFError:
                    text = ""
            if not text:
                print("No input. Example: python main.py --mode property \"M1 4BT\"")
                return
            run_property_pipeline_for_text(text)
            return
        print(f"Unknown --mode value: {argv[1]!r}. Use {MODE_CONTRACT!r} or {MODE_PROPERTY!r}.")
        return

    if argv and argv[0] in ("--contract", "--phase3-contract"):
        run_contract_integration_test()
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
        print("  python main.py --contract")
        print("  python main.py --mode contract")
        print('  python main.py --mode property "M1 4BT"')
        print("  python main.py --auto-test   # intent: contract vs property")
        print("  python main.py --contract-norm-test")
        print("  python main.py --contract-actions-test")
        print("  python main.py --missing-clause-test")
        print("  python main.py --flagged-clause-test")
        print("  python main.py --verdict-test")
        print("  python main.py --contract-demo")
        print("  python main.py --contract-batch-test")
        print("  python main.py --contract-human-test   # Phase 4: human next steps / evidence / risk")
        print("  python main.py --contract-final-display-test   # Phase 4: unified final_display block")
        print("  python main.py --contract-completeness-test   # Phase 4: completeness / missing info")
        print("  python main.py --contract-direct-answer-test   # Phase 4: direct answer / decision")
        print("  python main.py --contract-confidence-test   # Phase 4: result confidence layer")
        print("  python main.py --contract-urgency-test   # Phase 4 Part 9: urgency & priority")
        print("  python main.py --contract-decision-factors-test   # Phase 4 Part 10: decision factors")
        return

    run_main_flow(text, source="cli_argv")


if __name__ == "__main__":
    main()
