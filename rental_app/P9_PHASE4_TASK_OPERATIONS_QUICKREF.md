# P9 Phase4 Task Operations Quick Reference

---

## Create Task

| | |
|---|---|
| Method | `POST` |
| Path | `/tasks` |
| Body | `{"sources": [...], "limit_per_source": 10, "budget": 1500, ...}` |
| Response | `{"task_id": "a1b2c3d4e5f6", "status": "queued"}` |
| Notes | Returns immediately; task runs in background thread. |

---

## Get Task

| | |
|---|---|
| Method | `GET` |
| Path | `/tasks/{task_id}` |
| Response fields | `task_id`, `status`, `task_type`, `stage`, `created_at`, `updated_at`, `input_summary`, `degraded`, `elapsed_seconds`, `error`, `last_error_at`, `result` (only on success/degraded) |
| 404 | `{"error": "task_not_found", "task_id": "..."}` |

---

## List Tasks

| | |
|---|---|
| Method | `GET` |
| Path | `/tasks` |
| Query params | `mode` — `active` (default, queued/running only) or `recent` (all statuses); `limit` — max items (default 30, max 100) |
| Response | `{"tasks": [{task_id, status, task_type, stage, ...}, ...]}` |

Examples:
- `GET /tasks` — active tasks only (backward compatible)
- `GET /tasks?mode=recent` — last 30 tasks, all statuses
- `GET /tasks?mode=recent&limit=5` — last 5 tasks

---

## Task Stats

| | |
|---|---|
| Method | `GET` |
| Path | `/tasks/stats` |
| Response | `{"total": 12, "by_status": {"success": 8, "failed": 2, "interrupted": 1, "running": 1}}` |

---

## Task System Status

| | |
|---|---|
| Method | `GET` |
| Path | `/tasks/system` |
| Response | `{"queued_count": 1, "running_count": 2, "success_count": 10, "failed_count": 1, "degraded_count": 1, "max_concurrent_tasks": 2}` |

---

## Persisted Fields

All `TaskRecord` fields are persisted to `.task_store.json`:

| Field | Persisted | Notes |
|-------|-----------|-------|
| `task_id` | ✅ | |
| `status` | ✅ | queued/running → interrupted on restart |
| `task_type` | ✅ | |
| `stage` | ✅ | |
| `created_at` | ✅ | |
| `updated_at` | ✅ | |
| `input_summary` | ✅ | |
| `result` | ✅ | Can be large |
| `error` | ✅ | |
| `degraded` | ✅ | |
| `elapsed_seconds` | ✅ | |
| `last_error_at` | ✅ | |

---

## Restart Behavior

1. Process restarts → `TaskStore.__init__` loads `.task_store.json`.
2. Tasks in `queued`/`running` → re-marked as `interrupted`.
3. Terminal tasks (`success`/`failed`/`degraded`/`timeout`) → unchanged.
4. File missing or corrupt → starts with empty store, logs a warning.

---

## Status Meanings

| Status | Meaning |
|--------|---------|
| `queued` | Submitted, waiting for Semaphore |
| `running` | Background thread actively executing |
| `success` | Completed successfully |
| `degraded` | Completed with partial data |
| `failed` | Execution error |
| `timeout` | Exceeded time limit |
| `interrupted` | Process restarted while task was queued/running |

---

## Notes

- Lightweight JSON persistence — not a production queue system.
- Single worker only; not shared across gunicorn workers.
- TTL: finished tasks expire after 1 hour.
- Max capacity: 200 tasks (oldest evicted first).
- Persist path configurable via `RENTALAI_TASK_STORE_PATH` env var.
