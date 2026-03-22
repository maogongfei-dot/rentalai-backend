# P10 Phase1 Data Integration

---

## 1. Data Flow Before

在本轮接入前：

- task 生命周期主要由 `TaskStore`（内存 + JSON）维护，接口可查但数据库沉淀不足。
- analysis 结果主要停留在运行时 `result`（task 内）与 API 返回体中，缺少可复用历史层。
- property 虽已写入 `data/listings.json`，但属于文件型存储，缺少统一结构化查询入口。
- 系统整体更偏“运行时工具链”，数据积累能力有限。

---

## 2. TaskRecord Integration

TaskRecord 已按生命周期接入数据库（SQLite）：

- **task 创建（queued）**
  - 触发点：`TaskStore.create(...)`
  - 写入：`task_id`、`task_type`、`status=queued`、`input_summary`、`created_at`

- **task 开始（running）**
  - 触发点：`TaskStore.mark_running(...)`
  - 更新：`status=running`、`started_at`、`updated_at`

- **task 终态（success/failed/degraded）**
  - 触发点：`TaskStore.mark_success(...)` / `mark_failed(...)`
  - 更新：
    - `status`（success / degraded / failed）
    - `result_summary`（成功/降级时）
    - `error`（失败时）
    - `finished_at`、`updated_at`

说明：

- 不改变现有 task API，仅增加数据库镜像写入。
- JSON 持久化路径仍保留，支持低风险回退。

---

## 3. AnalysisRecord Integration

本轮接入流程：

- 接入的是最核心异步分析流程：`_run_analysis_task`（`run_multi_source_analysis` 路径）。

写入逻辑：

- 分析成功后写入 `analysis_records`：
  - `analysis_type=multi_source_analysis`
  - `input_summary` / `input_hash`
  - `result_summary`
  - `source=async_task`
  - `created_at`

复用（cache）行为：

- 已实现“避免重复计算”最小版本：
  - 执行前按 `analysis_type + input_hash` 查询最近记录；
  - 命中且未过期时直接复用 `reusable_result`；
  - 当前任务直接 `success`（`elapsed_seconds=0.0`），跳过重新分析；
  - 并写入一条 `analysis_records`（`source=cache_hit`）用于审计。

可配置项：

- `RENTALAI_ANALYSIS_CACHE_ENABLED`（默认启用）
- `RENTALAI_ANALYSIS_CACHE_MAX_AGE_SECONDS`（默认 1800 秒）

---

## 4. PropertyRecord Integration

本轮接入位置：

- `data/storage/listing_storage.py` 的 `save_listings(...)`。

接入方式：

- 保持 JSON 主落盘不变；
- 在 JSON 保存成功后，镜像 upsert 到 `property_records`。

字段（最小）：

- `source`
- `listing_url`（来自 `source_url/listing_url`）
- `title`
- `postcode`
- `price`（`rent_pcm` 优先）
- `bedrooms`
- `summary`
- `created_at` / `updated_at`

---

## 5. Query Capability

已新增最小查询接口：

- `GET /records/tasks`：最近任务记录
- `GET /records/analysis`：最近分析记录
- `GET /records/properties`：最近房源记录（附加能力，不影响最小目标）

可观察数据：

- 任务状态演进与时间戳
- 分析输入/输出摘要与 cache 命中来源
- 房源基础字段沉淀

---

## 6. Data Reuse Behavior

已实现“避免重复计算”。

判断规则：

- `analysis_type` 相同；
- `input_summary` 生成的 `input_hash` 相同；
- 记录未超过 cache 最大有效期；
- 记录中存在 `reusable_result`。

命中后行为：

- 直接复用结果，不重新调用核心分析；
- task 生命周期保持完整（queued -> running -> success）；
- `analysis_records` 写入 `cache_hit` 事件，便于后续观察复用率。

---

## 7. Impact on System

对现有系统影响：

- **结构影响小**：主要是“旁路写入”，未重构核心逻辑与接口协议。
- **性能收益**：重复输入可直接复用，减少重复分析开销。
- **可靠性影响**：SQLite 写入失败不阻断主流程（best-effort），低风险可回退。
- **运维收益**：任务/分析/房源形成最小结构化数据面，便于排查与产品化演进。

---

## 8. Remaining Gaps

- 任务与分析记录尚未建立显式关联键（如 `task_id` 级关联）。
- 用户层数据未接入（历史、收藏、对比）。
- 查询能力仍为最小版（无复杂筛选、分页游标、索引优化策略）。
- cache 策略较粗（仅基于输入 hash + TTL，暂无质量/版本维度控制）。

---

## 9. Recommended Next Step

建议进入：**P10 Phase1 - Step3《数据关联 + 最小查询增强》**。

优先项：

1. 给 `analysis_records` 增加与 task 的关联信息（最小关联键）；
2. 增加时间范围 + limit/offset 的轻量查询能力；
3. 输出 cache 命中率观测字段，作为后续优化依据。
