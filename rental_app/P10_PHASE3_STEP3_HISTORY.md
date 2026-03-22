# P10 Phase3 Step3 History

## 1. Goal

在 Phase3 Step1（主流程）与 Step2（结果页结构化）之后，补齐**最小产品闭环**：分析完成后把**用户可读摘要 + Step2 的 `display_payload`** 写入持久化存储；用户通过 **`/history`** 查看自己的最近记录，并可跳转回 **`/result/{task_id}`** 复用现有结果页与展示逻辑。

## 2. Save Flow

1. 用户完成异步任务并打开 **`/result/{task_id}`**，轮询到 **`success` / `degraded`** 后，`result_view_model.js` 渲染 **ready** 态。
2. 同一路径末尾调用 **`RentalAIHistoryShelf.trySaveCompletedResult(vm)`**（见 `history_shelf.js`）。
3. 使用 **`sessionStorage`** 键 `rentalai_ui_saved_task_{task_id}` **幂等**：同一会话、同一任务只自动 POST 一次（避免刷新重复插入）。
4. 浏览器 **`POST /records/ui-history`**，Body：`task_id`、`input_value`（由 `GET /tasks` 的 `input_summary` 推导）、`display_payload`（即 Step2 的 view model）、`raw_task_snapshot`（完整 task 状态，服务端可截断）。
5. 服务端 **`insert_analysis_record`** 写入 SQLite **`analysis_records`**，`analysis_type = p10_ui_history`，`input_summary` 含 **`history_task_id`**（用于签名与区分任务，见 `normalize_analysis_input_signature` 扩展）。

## 3. Saved Fields

| 层级 | 字段 |
|------|------|
| **DB 行** | `id`（即 **record_id**）、`user_id`、`analysis_type`、`created_at`、`explain_summary`、`pros` / `cons` / `risk_flags`（JSON 列）、`input_summary`（JSON）、`result_summary`（JSON）、`source=ui_phase3` |
| **result_summary（saved_result_payload_v1）** | `schema`、`task_id`、`user_id`、`input_value`、`display_payload`（Step2 结构）、`raw_task_snapshot`（可选，过大时服务端截断为 prefix + 元数据） |

列表 API 再映射为 **`history_item_view`**：`record_id`、`created_at`、`task_id`、`input_value`、`title`、`final_score`、`verdict`、`summary_line`。

## 4. History Page

- **路径**：**`/history`**（静态 `history.html`）。
- **数据**：**`GET /records/ui-history?limit=50`**（需 Bearer，与任务 API 同一用户）。
- **表格列**：When（`created_at`）、Input（`input_value` 截断）、Title、Score、Verdict、**View** 链接。

## 5. Detail View

- **方案 A（采用）**：**View → `/result/{task_id}`**，完全复用 Step2 结果页与 **`buildResultViewModel`**。
- **补充 API**：**`GET /records/ui-history/{record_id}`** 返回单条快照（含 `saved_result_payload`），用于后续若 task 已过期时做「从快照渲染」——当前主 UX 仍以 task 为准。

## 6. User Binding

- 与现有 P10 一致：**Bearer token → `user_id`**（`POST /tasks` 同用户）。
- 隐式 guest：`/auth/register` + `/auth/login` 写入 `localStorage`；**`analysis_records.user_id`** 与该用户绑定。
- 代码上无硬编码匿名 ID；后续接入正式登录时只需替换前端拿 token 的方式，**服务端已按 `user_id` 过滤**。

## 7. Error Handling

| 场景 | 行为 |
|------|------|
| 无历史 | 文案 **No analysis history yet** |
| 保存失败 | 结果页横幅 **Failed to save analysis record**（仍展示分析结果） |
| 列表接口失败 | **Failed to load history** |
| 单条不存在 | API **404** + `Record not found`（`GET /records/ui-history/{id}`） |

## 8. Current Limitations

- **依赖 in-memory task**：`/result/{task_id}` 在进程重启或 TTL 过期后可能 404，历史里仍有快照但当前 UI 未实现「从 record 回放」。
- **自动保存**仅在一次会话内对同一 `task_id` 触发一次；刻意「再存一条」需后续显式按钮或清 `sessionStorage`。
- **`raw_task_snapshot`** 体量大时会被截断，仅适合排障而非完整审计。
- 历史列表**无分页**，仅最近 50 条（可调 `limit`）。

## 9. Next Step

- 当 **`GET /tasks/{id}`** 404 时，回退 **`GET /records/ui-history/{record_id}`** 或按 `task_id` 查最新快照并渲染（只读）。
- 历史页增加 **record_id** 直链 **`/history/record/{id}`** 或 query，与 task 解耦。
- 显式 **「Save to history」** 与 **删除记录**。
