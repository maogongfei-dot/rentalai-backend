# P10 Phase1 Cache Strategy

---

## 1. Current Repetition Problem

当前最容易重复计算的流程：

- 异步 `POST /tasks` 触发的 `run_multi_source_analysis`（Batch 与 Agent 两个入口都会走这条核心路径）。
- 同一用户短时间重复点击、不同入口提交同一条件（如预算/邮编/sources 相同）会重复跑 scraper + analysis。

最易浪费资源点：

- 重复启动抓取与批量分析，导致 CPU/IO 占用、队列等待和整体延迟上升。

---

## 2. Chosen Cache Strategy

采用策略：**数据库复用式缓存（基于 `analysis_records`）**。

核心方式：

- 先生成稳定输入签名（`input_signature` + `input_hash`）；
- 查询最近可复用分析记录；
- 命中则直接复用 `reusable_result`，跳过重跑；
- 未命中则正常执行并写入分析记录。

为什么适合当前阶段：

- 不引入 Redis/Memcached；
- 复用已落地 SQLite 数据层；
- 低改动、低风险、可回退。

---

## 3. Cache Key / Input Signature

“相同输入”判断方式：

- 使用标准化后的输入摘要生成 hash（SHA-256）。
- 标准化字段：
  - `sources`（去空、lower、去重、排序）
  - `limit_per_source`
  - `budget`
  - `target_postcode`（trim + upper）

说明：

- 通过排序与规范化，避免“字段顺序不同、source 顺序不同”造成误 miss。

---

## 4. Cache Hit Rules

命中条件：

1. `analysis_type` 相同（当前：`multi_source_analysis`）；
2. `input_hash` 相同；
3. 记录未超过 TTL（`RENTALAI_ANALYSIS_CACHE_MAX_AGE_SECONDS`）；
4. 历史记录为可复用结果（`summary.success=True`、`degraded=False`、`cacheable=True`）；
5. 存在完整 `reusable_result`。

命中后行为：

- 直接返回缓存结果，跳过分析执行；
- task 正常进入 `success`；
- 记录最小日志：`cache hit`；
- 写入一条 `analysis_records`（`source=cache_hit`）用于审计。

---

## 5. Cache Miss Rules

不命中条件（任一满足）：

- 无匹配 `input_hash`；
- 匹配记录超出 TTL；
- 匹配记录不是可复用成功结果；
- 无 `reusable_result`。

miss 后行为：

- 正常执行 analysis；
- 完成后写入 `analysis_records`；
- 记录最小日志：`cache miss`。

---

## 6. What Is Cached vs Not Cached

会缓存（可复用）：

- `success=True` 且 `degraded=False` 的核心异步分析结果。

不会缓存（不复用）：

- `failed`；
- `degraded`（部分失败，不作为稳定复用结果）；
- 缺失 `reusable_result` 的记录；
- 超过 TTL 的旧记录。

原因：

- 当前目标优先保证复用结果的稳定性与可预测性，避免把部分失败结果扩散给后续请求。

---

## 7. API / System Impact

对系统影响：

- 无破坏性接口变更，现有 task API 保持兼容。
- 缓存命中时，task `result` 增加 `_cache.hit=true` 标记（兼容增强）。
- 新增最小日志：`cache hit / cache miss`。
- 整体可降低重复计算带来的耗时与资源压力。

---

## 8. Remaining Gaps

- 仅覆盖一个核心 analysis 流程，未扩展到全部分析路径。
- 仍为单节点数据库复用，不是独立分布式缓存系统。
- 缺少命中率/节省耗时的系统化统计看板。
- 尚未引入“相似输入”语义缓存（当前仅稳定签名相同才命中）。

---

## 9. Recommended Next Step

建议进入：**P10 Phase1 - Step4《缓存观测 + 关联增强》**。

优先事项：

1. 为缓存命中添加最小指标统计（命中率、平均节省耗时）；
2. 把 `analysis_records` 与 `task_id` 建立显式关联；
3. 在保持低风险前提下评估是否允许特定 degraded 结果复用策略。
