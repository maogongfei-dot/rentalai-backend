"""In-process async task store for RentalAI.

Provides a lightweight TaskStore backed by a plain dict — no database,
no Redis, no external broker.  Suitable for single-worker deployments
where losing task state on process restart is acceptable.
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

_logger = logging.getLogger("rentalai.tasks")

_TASK_TTL_SECONDS = 600  # auto-expire after 10 min


@dataclass
class TaskRecord:
    task_id: str
    status: str  # queued | running | success | failed | timeout
    created_at: str
    updated_at: str
    input_summary: dict[str, Any] = field(default_factory=dict)
    result: dict[str, Any] | None = None
    error: str | None = None
    degraded: bool = False
    elapsed_seconds: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class TaskStore:
    """Thread-safe in-process task store.

    Limitations
    -----------
    * State lives only in the current process — lost on restart.
    * Not shared across gunicorn workers (each worker has its own store).
    * No persistent storage; purely memory-backed.
    * Max capacity is bounded by ``max_tasks``; oldest tasks are evicted
      when the limit is reached.
    """

    def __init__(self, *, max_tasks: int = 200, ttl: int = _TASK_TTL_SECONDS):
        self._tasks: dict[str, TaskRecord] = {}
        self._lock = threading.Lock()
        self._max = max_tasks
        self._ttl = ttl

    def create(self, input_summary: dict[str, Any] | None = None) -> TaskRecord:
        now = datetime.now(timezone.utc).isoformat()
        rec = TaskRecord(
            task_id=uuid.uuid4().hex[:12],
            status="queued",
            created_at=now,
            updated_at=now,
            input_summary=input_summary or {},
        )
        with self._lock:
            self._maybe_evict()
            self._tasks[rec.task_id] = rec
        _logger.info("[TASK] created %s", rec.task_id)
        return rec

    def get(self, task_id: str) -> TaskRecord | None:
        with self._lock:
            return self._tasks.get(task_id)

    def mark_running(self, task_id: str) -> None:
        self._update(task_id, status="running")

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
        )

    def mark_failed(self, task_id: str, error: str, *, elapsed: float | None = None) -> None:
        self._update(task_id, status="failed", error=error, elapsed_seconds=elapsed)

    def mark_timeout(self, task_id: str, *, elapsed: float | None = None) -> None:
        self._update(task_id, status="timeout", error="task timed out", elapsed_seconds=elapsed)

    def list_active(self) -> list[dict[str, Any]]:
        with self._lock:
            return [
                {"task_id": r.task_id, "status": r.status, "created_at": r.created_at}
                for r in self._tasks.values()
                if r.status in ("queued", "running")
            ]

    def _update(self, task_id: str, **fields: Any) -> None:
        with self._lock:
            rec = self._tasks.get(task_id)
            if rec is None:
                return
            for k, v in fields.items():
                if hasattr(rec, k):
                    setattr(rec, k, v)
            rec.updated_at = datetime.now(timezone.utc).isoformat()
        _logger.info("[TASK] %s -> %s", task_id, fields.get("status", "update"))

    def _maybe_evict(self) -> None:
        """Remove expired tasks or oldest when capacity is reached."""
        now = time.time()
        expired = [
            tid
            for tid, rec in self._tasks.items()
            if (now - _iso_epoch(rec.created_at)) > self._ttl
            and rec.status not in ("queued", "running")
        ]
        for tid in expired:
            del self._tasks[tid]
        while len(self._tasks) >= self._max:
            oldest = min(self._tasks, key=lambda t: self._tasks[t].created_at)
            del self._tasks[oldest]


def _iso_epoch(iso: str) -> float:
    try:
        return datetime.fromisoformat(iso).timestamp()
    except (ValueError, TypeError):
        return 0.0
