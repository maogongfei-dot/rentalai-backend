"""
RentalAI repo root: quick test entry for the Phase 1 chat router.

Usage (from repo root):
  python main.py "Is my deposit protected?"
  python main.py
"""

from __future__ import annotations

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
    print("intent:", result.get("intent"))
    print("source_module:", result.get("source_module"))
    print("--- response_text ---")
    print(result.get("response_text") or "")


if __name__ == "__main__":
    main()
