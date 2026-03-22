# P9 Phase3 Task API Quick Reference

---

## Create Task

- **Method:** `POST`
- **Path:** `/tasks`
- **Request body:**

```json
{
  "sources": ["rightmove", "zoopla"],
  "limit_per_source": 10,
  "budget": 1500.0,
  "target_postcode": "SW1A",
  "headless": true,
  "persist": true
}
```

All fields optional. Defaults: `limit_per_source=10`, `headless=true`, `persist=true`.

- **Response:**

```json
{
  "task_id": "a1b2c3d4e5f6",
  "status": "queued"
}
```

---

## Get Task Status

- **Method:** `GET`
- **Path:** `/tasks/{task_id}`
- **Running response:**

```json
{
  "task_id": "a1b2c3d4e5f6",
  "status": "running",
  "created_at": "2026-03-21T15:00:00+00:00",
  "updated_at": "2026-03-21T15:00:01+00:00",
  "degraded": false,
  "elapsed_seconds": null,
  "error": null
}
```

- **Success response (includes `result`):**

```json
{
  "task_id": "a1b2c3d4e5f6",
  "status": "success",
  "created_at": "2026-03-21T15:00:00+00:00",
  "updated_at": "2026-03-21T15:01:15+00:00",
  "degraded": false,
  "elapsed_seconds": 75.3,
  "error": null,
  "result": { "success": true, "analysis_envelope": { "..." : "..." } }
}
```

- **Not found:** HTTP 404

```json
{ "error": "task_not_found", "task_id": "nonexistent" }
```

---

## List Active Tasks

- **Method:** `GET`
- **Path:** `/tasks`
- **Response:**

```json
{
  "tasks": [
    { "task_id": "a1b2c3d4e5f6", "status": "running", "created_at": "..." }
  ]
}
```

---

## Status Meanings

| Status | Meaning |
|--------|---------|
| `queued` | Task created, background thread not yet started |
| `running` | Background thread is executing analysis |
| `success` | Completed successfully; `result` contains full output |
| `failed` | Exception during execution; `error` describes the failure |
| `timeout` | Execution timed out (reserved) |
| `degraded` | Completed with partial source failures; `result` available, `degraded=true` |

---

## Notes

- This is the **minimal skeleton** version — in-process dict storage, single worker only.
- All existing sync endpoints (`/analyze`, `/analyze-batch`, etc.) remain fully operational.
- Task records auto-expire after 10 minutes and are capped at 200 entries.
