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
- **写入**：`analysis_history_writer` 在成功响应后追加；房源 **`POST /api/ai/query`**；合同 **`/api/contract/analysis/text`**、**`/file-path`**、**`/upload`**。请求体可选 **`userId` / `user_id`**，缺省桶 **`guest`**。存储行内字段名为 **`userId`**（与读接口 query 一致）；用户文件行内为 **`user_id`**（与 **`/auth/*`** 响应一致）。
- **读取**：**`GET /api/analysis/history/records`** → `{ success, message, records }`。**Phase 5 第五轮 Step3**：须 **`Authorization: Bearer <token>`**；桶 id 以 token 解析的 user 为准（可选 `userId` query 须与之一致）。见 **`auth_http_helpers.resolve_user_id_from_auth_header`**、**`server_history_api.js`**。

## 最小受保护 API（Phase 5 第五轮 — **阶段完成**）

- **会话形态**：进程内 **session/token placeholder**（`auth_session_store`：`secrets.token_hex` → userId），**非** JWT；无过期、无 refresh；**logout** 使 token 失效。
- **已保护接口范围（仅此一步）**：**`GET /api/analysis/history/records`** 须 **`Authorization: Bearer`**；有效 token 才返回该用户 JSON 历史；**其它**路由（分析写入、`/auth/me` 等）行为与第三轮/既有逻辑一致，**未**做全站中间件。
- **前端**：`rentalai_bearer` + `rentalai_auth_type`；`server_history_api.js` 统一注入 Bearer；访客仍走 **localStorage guest**，不调用受保护读接口。
- **刻意未做**：**JWT**、**过期/刷新**、**全接口强制鉴权**、**history 写入与 token 绑定**、**bcrypt/Argon2**、**数据库**由 JSON 升级；见主 **`README.md`**「Phase 5 第五轮 Step5」。

## 本轮未做（后续增强）

- 密码：**bcrypt/Argon2**、盐与策略；仅当前 **SHA-256 演示级**哈希。
- 会话：**HttpOnly Cookie**、刷新令牌；当前 Bearer 仍为**进程内**映射。
- 安全扩展：分析类 **POST** 与 body **`userId`** 对齐 Bearer；全路由统一鉴权中间件。
- 产品：**guest→user 迁移**、分页/搜索、冲突合并、多设备同步；**数据库**由 JSON 迁移至业务库。
