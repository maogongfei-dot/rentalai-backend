# P10 Phase1 Data Models Quick Reference

---

## TaskRecord

- fields:
  - `id`
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
- purpose:
  - 保存任务生命周期与关键摘要，支撑任务历史回查与故障排查。

---

## AnalysisRecord

- fields:
  - `id`
  - `analysis_type`
  - `input_hash`
  - `input_summary`
  - `result_summary`
  - `raw_result_ref`
  - `source`
  - `created_at`
- purpose:
  - 记录分析行为的结构化历史，为后续历史分析与重复输入识别提供基础。

---

## PropertyRecord

- fields:
  - `id`
  - `source`
  - `listing_url`
  - `title`
  - `postcode`
  - `price`
  - `bedrooms`
  - `summary`
  - `created_at`
  - `updated_at`
- purpose:
  - 构建最小房源索引层，支持后续收藏、对比和历史列表复用。

---

## Notes

- 当前为最小可用数据层（SQLite + 现有 JSON 双轨）。
- 后续可继续扩展实体关联、用户层模型、筛选分页与索引策略。
