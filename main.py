"""
RentalAI repo root: quick test entry for the Phase 1 chat router.

Usage (from repo root):
  python main.py "Is my deposit protected?"
  python main.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.chat import handle_chat_request


def main() -> None:
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    argv = sys.argv[1:]
    if argv:
        text = " ".join(argv)
    else:
        try:
            text = input("Enter message: ").strip()
        except EOFError:
            text = ""
    if not text:
        print("No input. Pass text as args or stdin.")
        return
    result = handle_chat_request(text)
    pip = result.get("property_input_parsed") or {}
    if pip:
        print("input_type:", pip.get("input_type"))
        print("detected_links:", pip.get("detected_links"))
        print("detected_postcodes:", pip.get("detected_postcodes"))
        print("property_reference:", json.dumps(result.get("property_reference") or {}, indent=2, ensure_ascii=False))
        print("property_input_detected:", result.get("property_input_detected"))
    print("scope:", result.get("scope"), "| handling:", result.get("scope_handling"))
    print("scope_confidence:", result.get("scope_confidence"))
    print("matched_scope_keywords:", result.get("matched_scope_keywords"))
    print("scope_message:", repr(result.get("scope_message") or ""))
    print("intent:", result.get("intent"))
    print("source_module:", result.get("source_module"))
    print("risk_tier:", result.get("risk_tier"))
    print("--- response_text ---")
    print(result.get("response_text") or "")
    print("--- followup_suggestions ---")
    for i, line in enumerate(result.get("followup_suggestions") or [], 1):
        print(f"  {i}. {line}")
    print("next_step_prompt:", result.get("next_step_prompt") or "")
    caps = result.get("available_capabilities") or []
    if caps:
        print("available_capabilities:", ", ".join(caps))
    print("priority_order:", result.get("priority_order"))
    print("user_signals_summary:", result.get("user_signals_summary") or "")
    print("--- detected_preferences ---")
    print(json.dumps(result.get("detected_preferences") or {}, indent=2, ensure_ascii=False))
    cr = result.get("comparison_result")
    if cr:
        print("--- comparison ---")
        print("comparison_inputs:", json.dumps(result.get("comparison_inputs") or {}, indent=2, ensure_ascii=False))
        print("comparison_summary:", cr.get("comparison_summary"))
        print("comparison_points:", json.dumps(cr.get("comparison_points") or [], indent=2, ensure_ascii=False))
        print("missing_information:", cr.get("missing_information"))


if __name__ == "__main__":
    main()
