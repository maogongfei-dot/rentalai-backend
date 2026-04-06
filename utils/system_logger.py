"""
Append ``system_result`` shells to a local JSON Lines file (Phase 3 Part 35).
"""

from __future__ import annotations

import json
import os
from typing import Any

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_LOG_DIR = os.path.join(_ROOT, "logs")
_LOG_FILE = os.path.join(_LOG_DIR, "system_results.jsonl")


def log_system_result(system_result: dict[str, Any]) -> None:
    """Append one JSON object per line to ``logs/system_results.jsonl``; failures are non-fatal."""
    try:
        os.makedirs(_LOG_DIR, exist_ok=True)
        line = json.dumps(system_result, ensure_ascii=False) + "\n"
        with open(_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception as e:
        print("Logging failed:", e)
