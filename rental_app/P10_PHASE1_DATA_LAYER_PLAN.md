# P10 Phase1 Data Layer Plan

---

## 1. Current Data Gaps

当前主要数据缺口：

- **任务记录仅在内存 + JSON TaskStore**：虽然可恢复，但查询能力弱，不利于后续用户历史与后台统计。
- **分析结果缺少结构化历史表**：当前主要在 task `result` 内，缺少可独立检索的 analysis 记录。
- **房源记录主要在 `data/listings.json`**：已有持久化，但缺少统一查询接口和结构化产品层索引。
- **跨实体关联薄弱**：任务、分析、房源之间缺少统一数据层连接，难支撑后续收藏/对比/历史视图。

最危险缺口：

- 缺少可扩展的统一数据层，导致上线后难以做用户级功能（历史、收藏、回看、对比）与稳定运维分析。

---

## 2. Chosen Storage Solution

本阶段选择：**SQLite（stdlib `sqlite3`）+ 现有 JSON 双轨过渡**。

为什么适合当前阶段：

1. 零外部依赖，不引入 Redis/Postgres 集群，部署风险低。
2. 与当前单进程/轻量架构贴合，易于最小接入。
3. 可提供结构化查询能力（任务/分析/房源）并保留现有 JSON 兼容路径。
4. 后续可平滑迁移到更重存储（模型与字段先稳定，再迁移底座）。

为什么不是更重方案：

- 当前目标是“最小可用数据层”而非“分布式高并发数据库改造”。过早引入重系统会显著扩大变更风险与工作面。

---

## 3. Core Data Models

### TaskRecord

字段（SQLite `task_records`）：

- `id`（自增主键）
- `task_id`（唯一业务 ID）
- `task_type`
- `status`
- `input_summary`（JSON 文本）
- `result_summary`（JSON 文本）
- `error`
- `degraded`
- `created_at`
- `updated_at`
- `started_at`
- `finished_at`

用途：

- 保留任务生命周期最关键业务记录，支撑任务历史、失败排障和后续用户历史页。

### AnalysisRecord

字段（SQLite `analysis_records`）：

- `id`
- `analysis_type`
- `input_hash`
- `input_summary`（JSON 文本）
- `result_summary`（JSON 文本）
- `raw_result_ref`
- `source`
- `created_at`

用途：

- 将分析行为从 task 结果中“抽出可检索记录”，便于做分析历史、重复输入识别、统计看板。

### PropertyRecord（最小版）

字段（SQLite `property_records`）：

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

用途：

- 为后续收藏、对比、列表复用提供统一房源索引层（当前仍保留 JSON 作为主兼容存储）。

---

## 4. Initial Integration Scope

本轮实际接入：

- TaskStore 每次 create/update 的任务元数据同步写入 SQLite `task_records`。
- async 任务成功/降级后，写入一条核心分析记录到 `analysis_records`。
- 现有 `listing_storage.save_listings()` 在 JSON 落盘成功后，镜像 upsert 到 `property_records`。
- 新增最小查询接口：`GET /records/tasks`、`GET /records/analysis`、`GET /records/properties`。

本轮暂不接：

- 复杂筛选/分页/全文检索。
- 用户维度数据（用户表、收藏表、对比表）。
- 任务与分析、分析与房源的强关联外键建模。

---

## 5. API / Persistence Impact

现有接口影响：

- `POST /tasks` / `GET /tasks*` 保持兼容；原 TaskStore JSON 逻辑保留。
- 新增记录查询接口，不影响旧前端调用路径。

持久化变化：

- 任务：从“仅 JSON”升级为“JSON + SQLite 镜像”。
- 分析：在 async 任务成功路径新增 analysis record 写入。
- 房源：在现有 JSON 保存成功后镜像写入 SQLite。

新增最小查询接口：

- `GET /records/tasks?limit=30`
- `GET /records/analysis?limit=30`
- `GET /records/properties?limit=30`

---

## 6. Why This Is Minimal but Useful

- 保持现有系统运行方式不变，仅增加“结构化记录层”。
- 通过最少改动把三类关键数据纳入统一存储面。
- 既能立即支持运营回查，又为后续用户层功能提供可复用数据基础。
- 所有新增都可低风险回退（不移除旧 JSON 路径）。

---

## 7. Remaining Data Gaps

- 无用户维度（谁发起、谁收藏、谁比较）。
- 无实体关系层（task -> analysis -> properties）的强关联结构。
- 无高级查询能力（过滤、分页游标、索引优化）。
- 无数据保留策略（归档、清理、版本化）。

---

## 8. Recommended Next Step

建议进入：**P10 Phase1 - Step2《数据关联与查询能力增强》**。

优先事项：

1. 为 `task_records` 与 `analysis_records` 增加关联键（如 `task_id`）。
2. 增加最小分页和时间范围筛选。
3. 设计用户层最小模型（用户历史、收藏）并先接入只读查询链路。
