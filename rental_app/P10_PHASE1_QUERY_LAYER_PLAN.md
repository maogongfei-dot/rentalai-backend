# P10 Phase1 Query Layer Plan

---

## 1. Current Query Gaps

- 数据已能写入 SQLite，但历史读取能力不完整（此前缺少 task detail）。
- 路由层直接拼查询返回，缺少统一查询服务组织，后续扩展不方便。
- 用户历史/收藏/对比需要稳定的 task/analysis/property 查询基座。

---

## 2. Query Scope

本轮实际完成：

- `GET /records/tasks`（任务历史列表）
- `GET /records/tasks/{task_id}`（任务详情）
- `GET /records/analysis`（分析历史列表）
- `GET /records/properties`（房源历史列表）

本轮暂不做：

- 复杂筛选（按状态/来源/时间多条件组合）
- 完整分页系统（cursor/page token）
- 全文搜索与聚合统计查询

---

## 3. Task Query Design

### 任务历史接口

- Method: `GET`
- Path: `/records/tasks`
- 返回字段（最小）：
  - `task_id`
  - `task_type`
  - `status`
  - `input_summary`
  - `result_summary`
  - `error`
  - `created_at`
  - `updated_at`

用途：

- 提供“最近任务”历史视图基础，支持运营排查与后续用户历史页。

### 任务详情接口

- Method: `GET`
- Path: `/records/tasks/{task_id}`
- 返回字段（更完整）：
  - 列表字段 +
  - `degraded`
  - `started_at`
  - `finished_at`

用途：

- 支持单任务深度查看（完整生命周期和异常信息）。

---

## 4. Analysis Query Design

- Method: `GET`
- Path: `/records/analysis`
- 返回字段：
  - `analysis_type`
  - `input_hash`
  - `input_summary`
  - `result_summary`
  - `source`
  - `created_at`

用途：

- 支撑分析历史回看、缓存命中审计和后续复用策略评估。

---

## 5. Property Query Design

- Method: `GET`
- Path: `/records/properties`
- 返回字段：
  - `source`
  - `listing_url`
  - `title`
  - `postcode`
  - `price`
  - `bedrooms`
  - `updated_at`

用途：

- 提供房源基础记录查询面，为收藏/对比/历史列表做数据基础。

---

## 6. Service / Query Layer Structure

查询逻辑组织：

- DB 访问层：`data/storage/records_db.py`
  - 负责 SQL 与行转换。
- 查询服务层：`data/storage/records_query_service.py`
  - 负责字段裁剪、接口返回结构对齐。
- 路由层：`api_server.py`
  - 仅调用 service，避免 SQL 逻辑散落在路由。

这样组织原因：

- 保持最小改动同时提升可维护性；
- 为后续筛选/分页扩展预留干净入口。

---

## 7. Frontend Readiness

- 当前前端尚未接入历史页，但后端接口已具备最小调用条件（list + detail）。
- 后续接法（低风险）：
  1. 先在 debug 区增加只读历史调用；
  2. 再抽成独立小面板（任务历史 / 分析历史）；
  3. 最后与用户维度绑定（用户历史/收藏/对比）。

---

## 8. Why This Enables Productization

- 从“可写入”进化到“可查询”，数据才真正可用。
- 任务、分析、房源三条历史链可直接支撑产品化能力：
  - 用户历史
  - 收藏回看
  - 结果对比
  - 运营排障

---

## 9. Remaining Gaps

- 缺时间范围筛选与更细粒度过滤。
- 缺统一分页规范（当前仅 limit）。
- 缺用户维度关联（当前是全局记录视图）。
- 缺缓存命中率等观测聚合接口。

---

## 10. Recommended Next Step

建议进入：**P10 Phase1 - Step5《查询增强 + 用户历史雏形》**。

优先项：

1. 增加时间范围筛选（from/to）；
2. 增加最小 offset 分页；
3. 在不重构前端的前提下接入一个只读历史调试面板。
