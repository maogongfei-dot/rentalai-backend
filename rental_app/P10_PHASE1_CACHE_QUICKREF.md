# P10 Phase1 Cache Quick Reference

---

## Cache Key

- 基于标准化输入生成 `input_signature`，再生成 `input_hash`（SHA-256）。
- 标准化字段：`sources`（排序去重）、`limit_per_source`、`budget`、`target_postcode`。

---

## Hit

- 命中条件：同 `analysis_type` + 同 `input_hash` + 未过 TTL + 记录可复用。
- 命中处理：直接返回 `reusable_result`，跳过重跑，记录 `cache hit`。

---

## Miss

- 不命中：无记录/过期/不可复用/无可复用结果。
- miss 处理：正常执行 analysis，完成后写入记录，记录 `cache miss`。

---

## Stored Result

- 可复用：`success` 且非 `degraded` 的核心分析结果。
- 不复用：`failed`、`degraded`、过期结果。

---

## Notes

- 当前为数据库复用式缓存（SQLite `analysis_records`）。
- 不是独立缓存系统（无 Redis/Memcached）。
