"""In-process async task store for RentalAI — with lightweight JSON persistence.

Provides a thread-safe TaskStore backed by a plain dict, with optional
automatic flush to a local JSON file.  On startup the store attempts to
reload previous task records so that completed-task metadata survives
process restarts (running tasks are marked ``interrupted``).

No database, no Redis, no external broker.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_logger = logging.getLogger("rentalai.tasks")

_TASK_TTL_SECONDS = 3600  # keep finished tasks visible for 1 hour
_DEFAULT_PERSIST_PATH = os.environ.get(
    "RENTALAI_TASK_STORE_PATH",
    str(Path(__file__).resolve().parent / ".task_store.json"),
)

_TERMINAL_STATUSES = frozenset({"success", "failed", "degraded", "timeout", "interrupted"})


@dataclass
class TaskRecord:
    task_id: str
    status: str  # queued | running | success | failed | timeout | degraded | interrupted
    created_at: str
    updated_at: str
    input_summary: dict[str, Any] = field(default_factory=dict)
    result: dict[str, Any] | None = None
    error: str | None = None
    degraded: bool = False
    elapsed_seconds: float | None = None
    task_type: str = "multi_source_analysis"
    stage: str = ""
    last_error_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class TaskStore:
    """Thread-safe in-process task store with optional JSON persistence.

    Persistence
    -----------
    Every state mutation flushes the full store to a JSON file (default
    ``.task_store.json`` beside this module).  On ``__init__`` the file
    is loaded if it exists; any task previously in ``queued``/``running``
    state is re-marked as ``interrupted`` since the background thread
    that was executing it no longer exists.

    Limitations
    -----------
    * Still single-process — not shared across gunicorn workers.
    * The JSON file is not locked across processes; concurrent writers
      from multiple workers would overwrite each other.
    * ``result`` payloads can be large; persistence file may grow.
      TTL eviction keeps it bounded.
    """

    def __init__(
        self,
        *,
        max_tasks: int = 200,
        ttl: int = _TASK_TTL_SECONDS,
        persist_path: str | None = _DEFAULT_PERSIST_PATH,
    ):
        self._tasks: dict[str, TaskRecord] = {}
        self._lock = threading.Lock()
        self._max = max_tasks
        self._ttl = ttl
        self._persist_path: str | None = persist_path
        self._load()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create(
        self,
        input_summary: dict[str, Any] | None = None,
        *,
        task_type: str = "multi_source_analysis",
    ) -> TaskRecord:
        now = datetime.now(timezone.utc).isoformat()
        rec = TaskRecord(
            task_id=uuid.uuid4().hex[:12],
            status="queued",
            created_at=now,
            updated_at=now,
            input_summary=input_summary or {},
            task_type=task_type,
            stage="queued",
        )
        with self._lock:
            self._maybe_evict()
            self._tasks[rec.task_id] = rec
            self._flush_unlocked()
        _logger.info("[TASK] created %s (type=%s)", rec.task_id, task_type)
        return rec

    def get(self, task_id: str) -> TaskRecord | None:
        with self._lock:
            return self._tasks.get(task_id)

    def mark_running(self, task_id: str, *, stage: str = "running") -> None:
        self._update(task_id, status="running", stage=stage)

    def mark_success(
        self,
        task_id: str,
        result: dict[str, Any],
        *,
        degraded: bool = False,
        elapsed: float | None = None,
    ) -> None:
        self._update(
            task_id,
            status="degraded" if degraded else "success",
            result=result,
            degraded=degraded,
            elapsed_seconds=elapsed,
            stage="done",
        )

    def mark_failed(self, task_id: str, error: str, *, elapsed: float | None = None) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self._update(
            task_id,
            status="failed",
            error=error,
            elapsed_seconds=elapsed,
            stage="failed",
            last_error_at=now,
        )

    def mark_timeout(self, task_id: str, *, elapsed: float | None = None) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self._update(
            task_id,
            status="timeout",
            error="task timed out",
            elapsed_seconds=elapsed,
            stage="timeout",
            last_error_at=now,
        )

    def list_active(self) -> list[dict[str, Any]]:
        with self._lock:
            return [
                {"task_id": r.task_id, "status": r.status, "created_at": r.created_at}
                for r in self._tasks.values()
                if r.status in ("queued", "running")
            ]

    def list_recent(self, limit: int = 30) -> list[dict[str, Any]]:
        """Return the *limit* most-recent tasks (all statuses), newest first."""
        with self._lock:
            ordered = sorted(
                self._tasks.values(),
                key=lambda r: r.updated_at,
                reverse=True,
            )[:limit]
            return [
                {
                    "task_id": r.task_id,
                    "status": r.status,
                    "task_type": r.task_type,
                    "stage": r.stage,
                    "created_at": r.created_at,
                    "updated_at": r.updated_at,
                    "elapsed_seconds": r.elapsed_seconds,
                    "degraded": r.degraded,
                    "error": r.error,
                }
                for r in ordered
            ]

    def stats(self) -> dict[str, Any]:
        """Aggregate counts by status."""
        with self._lock:
            counts: dict[str, int] = {}
            for r in self._tasks.values():
                counts[r.status] = counts.get(r.status, 0) + 1
            return {"total": len(self._tasks), "by_status": counts}

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _update(self, task_id: str, **fields: Any) -> None:
        with self._lock:
            rec = self._tasks.get(task_id)
            if rec is None:
                return
            for k, v in fields.items():
                if hasattr(rec, k):
                    setattr(rec, k, v)
            rec.updated_at = datetime.now(timezone.utc).isoformat()
            self._flush_unlocked()
        _logger.info("[TASK] %s -> %s", task_id, fields.get("status", "update"))

    def _maybe_evict(self) -> None:
        """Remove expired tasks or oldest when capacity is reached."""
        now = time.time()
        expired = [
            tid
            for tid, rec in self._tasks.items()
            if (now - _iso_epoch(rec.created_at)) > self._ttl
            and rec.status in _TERMINAL_STATUSES
        ]
        for tid in expired:
            del self._tasks[tid]
        while len(self._tasks) >= self._max:
            oldest = min(self._tasks, key=lambda t: self._tasks[t].created_at)
            del self._tasks[oldest]

    # ------------------------------------------------------------------
    # JSON persistence
    # ------------------------------------------------------------------

    def _flush_unlocked(self) -> None:
        """Write entire store to JSON.  Caller must hold ``_lock``."""
        if not self._persist_path:
            return
        try:
            payload = {tid: rec.to_dict() for tid, rec in self._tasks.items()}
            tmp = self._persist_path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, ensure_ascii=False, indent=1)
            os.replace(tmp, self._persist_path)
        except Exception:
            _logger.warning("[TASK] persist flush failed", exc_info=True)

    def _load(self) -> None:
        """Load tasks from persisted JSON on startup."""
        if not self._persist_path or not os.path.isfile(self._persist_path):
            return
        try:
            with open(self._persist_path, encoding="utf-8") as fh:
                raw: dict[str, Any] = json.load(fh)
        except Exception:
            _logger.warning("[TASK] persist load failed — starting fresh", exc_info=True)
            return

        now = datetime.now(timezone.utc).isoformat()
        loaded = 0
        interrupted = 0
        for tid, data in raw.items():
            try:
                rec = TaskRecord(**{
                    k: v for k, v in data.items() if hasattr(TaskRecord, k)
                })
                if rec.status in ("queued", "running"):
                    rec.status = "interrupted"
                    rec.stage = "interrupted"
                    rec.error = rec.error or "Process restarted while task was in progress."
                    rec.last_error_at = now
                    rec.updated_at = now
                    interrupted += 1
                self._tasks[tid] = rec
                loaded += 1
            except Exception:
                _logger.warning("[TASK] skipping corrupt record %s", tid)
        _logger.info(
            "[TASK] loaded %d tasks from disk (%d marked interrupted)", loaded, interrupted
        )


def _iso_epoch(iso: str) -> float:
    try:
        return datetime.fromisoformat(iso).timestamp()
    except (ValueError, TypeError):
        return 0.0
