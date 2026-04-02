# Phase 5 Round3 — JSON persistence（第三轮阶段完成）

**Phase 5 第四轮补充**：已登录用户的**分析历史**优先经 HTTP 读写本目录下的 **`persistence_analysis_history.json`**（与前端 `loadAnalysisHistory` / `userId` 写入对齐）；**未登录**仍仅用浏览器 **localStorage**，不经过此文件。

**持久化方式**：本目录实现 **本地 JSON 文件**（stdlib + 原子写），非 PostgreSQL/SQLite 业务库。默认路径见各 `*_store.py`；可用环境变量覆盖。

## Users (`user_store` / `user_repository` / `user_auth_service`)

- **File**: `data/storage/persistence_users.json` (override: `RENTALAI_PERSISTENCE_USERS_JSON`).
- **Register / login 已持久化**：**`/auth/register`**、**`/auth/login`**、**`/auth/me`** 经 **`user_auth_service`** 读写该文件；`password_hash` + **`password_hash_algorithm`**（当前 **`sha256_v1`**，可扩展到 `password_hashing.py`）；**`created_at`** 为 UTC **ISO8601**。
- **Duplicate email**: `register_user` → `UserRepository.get_by_email`（邮箱小写归一）。

## Session tokens (`auth_session_store.py` — Phase 5 Round5 Step1)

- **内存占位**：`token_hex → user_id`（`secrets.token_hex` 签发）；**不落盘**；单进程有效。
- **API**：`issue_token`、`revoke_token`（logout）、`resolve_user_id`（Bearer 解析）、`build_auth_payload`（`auth_type`: **`session_placeholder`**）。
- **`/auth/register` / `/auth/login` 成功响应**含 **`auth: { token, auth_type }`**，并保留顶层 **`token`** 兼容旧前端。

## Analysis history (server-side JSON)

- **File**: `data/storage/persistence_analysis_history.json` (override: `RENTALAI_PERSISTENCE_ANALYSIS_HISTORY_JSON`).
- **写入**：`analysis_history_writer.persist_analysis_history`（房源/合同共用形状）在分析成功响应后追加；路由：房源 **`POST /api/ai/query`**；合同 **`/api/contract/analysis/text`**、**`/file-path`**、**`/upload`**。**`auth_http_helpers.resolve_history_write_user_id`**：**有 Bearer 时写入分桶仅以 token 解析的 `user_id` 为准**；body 可选 **`userId` / `user_id`** 仅作一致性校验（若声称非 guest 则须与 token 用户相同）。**无 Bearer** 时仅允许 **`guest`** 桶。未通过校验则不追加 JSON，但分析主响应仍返回，并带 **`history_write: { success, message }`**。存储行顶层字段名为 **`userId`**。
- **读取**：**`GET /api/analysis/history/records`** → `{ success, message, records }`；须 **`Authorization: Bearer`**；桶以 token 解析用户为准（可选 `userId` query 须一致）。见 **`server_history_api.js`**、前端 **`analysis_history_source.loadAnalysisHistory`**。
- **删除单条（Phase 5 第七轮 Step1）**：**`DELETE /api/analysis/history/records/{record_id}`** — 须 Bearer；**`resolve_user_id_from_auth_header`** 解析用户；仅当行内 **`userId`** 与 token 用户一致时物理删除；否则 **404**（无此 id）或 **403**（存在但属他人）。响应 **`{ success, message }`**。
- **清空当前用户全部（Phase 5 第七轮 Step2）**：**`DELETE /api/analysis/history/clear`** — 须 Bearer；遍历 `records`，**删除所有 `userId` 等于 token 用户的行**，其它用户行保留；响应 **`{ success, message, deleted_count }`**。

## 最小受保护 API（Phase 5 第五轮 + Phase 5 第六轮 — **history 读/写依赖 token/session placeholder**）

- **会话形态**：进程内 **session/token placeholder**（`auth_session_store`：`secrets.token_hex` → userId），**非** JWT；无过期、无 refresh；**logout** 撤销映射。
- **已保护范围**：**读** — **`GET /api/analysis/history/records`** 须 Bearer。**删** — **`DELETE /api/analysis/history/records/{record_id}`**、**`DELETE /api/analysis/history/clear`** 须 Bearer。**写** — 上述分析路由在追加服务端 JSON 历史时走 **`resolve_history_write_user_id`**（guest 免 Bearer；已登录须 Bearer）。**`/auth/me`** 等未加全站中间件。
- **前端**：`rentalai_bearer`；**`mergeAuthHeadersForFetch`**（`analysis_history_persist.js`）为分析 POST 带 **`Authorization`**；**`server_history_api.js`** 为历史 GET 带 Bearer；**访客**仍仅用 **localStorage** 统一摘要，不调用受保护读接口。
- **Phase 5 第六轮（Step1–Step5）产品结论**：**已登录用户**在分析成功且校验通过时 **自动写入云端 JSON 历史**；**访客**仍为 **仅本地** 历史；结果页有 **`history_write` 与轻提示**；历史页支持刷新与 cache-bust。**本轮不升级为完整安全体系**。

## 本轮未做（后续增强）

- **认证**：**JWT**、**过期/refresh**、**HttpOnly Cookie**；生产级密码 **bcrypt/Argon2**（当前演示级 SHA-256）。
- **服务端**：全路由统一鉴权中间件；**数据库**由 JSON 升级；多实例下 session 外置。
- **分析历史产品**：**单条删除**（第七轮 Step1）、**当前账号清空**（第七轮 Step2）已具备；**批量编辑**、分页与搜索、**guest→user 迁移**、**多设备冲突合并**；前端 token **失效统一 UX**（除现有 `#history-server-notice` 外）。
