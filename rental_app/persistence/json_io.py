"""Shared JSON file I/O for persistence skeleton (stdlib, thread-safe writes)."""

from __future__ import annotations

import json
import os
import tempfile
import threading
from pathlib import Path
from typing import Any

_JSON_LOCKS: dict[str, threading.Lock] = {}
_JSON_LOCKS_GUARD = threading.Lock()


def _lock_for_path(path: Path) -> threading.Lock:
    key = str(path.resolve())
    with _JSON_LOCKS_GUARD:
        if key not in _JSON_LOCKS:
            _JSON_LOCKS[key] = threading.Lock()
        return _JSON_LOCKS[key]


def load_json_object(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    """Read JSON object from path; on missing/invalid return a copy of default."""
    path = Path(path)
    if not path.is_file():
        return dict(default)
    try:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
        if isinstance(data, dict):
            return data
    except (OSError, UnicodeError, json.JSONDecodeError, TypeError):
        pass
    return dict(default)


def save_json_atomic(path: Path, data: dict[str, Any]) -> None:
    """Write JSON atomically (temp + replace) under per-path lock."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True)
    lock = _lock_for_path(path)
    with lock:
        fd, tmp = tempfile.mkstemp(
            prefix=".rentalai_json_",
            suffix=".tmp",
            dir=str(path.parent),
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(text)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, path)
        except BaseException:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise
