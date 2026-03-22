# P10 Phase1 History API Quick Reference

---

## List Tasks

- Method: `GET`
- Path: `/records/tasks`
- Fields returned:
  - `task_id`
  - `task_type`
  - `status`
  - `input_summary`
  - `result_summary`
  - `error`
  - `created_at`
  - `updated_at`

---

## Get Task Detail

- Method: `GET`
- Path: `/records/tasks/{task_id}`
- Fields returned:
  - `task_id`
  - `task_type`
  - `status`
  - `input_summary`
  - `result_summary`
  - `error`
  - `degraded`
  - `created_at`
  - `updated_at`
  - `started_at`
  - `finished_at`

---

## List Analysis

- Method: `GET`
- Path: `/records/analysis`
- Fields returned:
  - `analysis_type`
  - `input_hash`
  - `input_summary`
  - `result_summary`
  - `source`
  - `created_at`

---

## List Properties

- Method: `GET`
- Path: `/records/properties`
- Fields returned:
  - `source`
  - `listing_url`
  - `title`
  - `postcode`
  - `price`
  - `bedrooms`
  - `updated_at`

---

## Notes

- 当前为最小历史查询层（list + task detail）。
- 后续可接用户历史/收藏/对比。
