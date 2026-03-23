# User System

## 1. Goal

将 Phase3 前期依赖的「隐式 guest 注册」改为**显式注册 / 登录**的最小闭环：用户数据（任务、UI 历史快照）绑定真实 **`user_id`**；未登录用户**不能**发起需要鉴权的分析流程；历史列表仅展示当前登录用户的数据。

## 2. User Model

沿用 SQLite **`users`** 表（`records_db`）：

| 字段 | 说明 |
|------|------|
| `id` | `user_id`（UUID hex） |
| `email` | 唯一、小写存储 |
| `password` | SHA-256 摘要（非明文、非盐扩展，保持最小实现） |
| `created_at` | ISO 时间 |

辅助函数：`email_exists`、`get_user_by_id`、`create_user`、`verify_user`。

## 3. Register Flow

- 页面 **`/register`**（`register.html`）：email + password → **`POST /auth/register`**。
- 邮箱已存在 → API 返回 **`User already exists`**（400）。
- 成功 → 返回 **`token` + `user_id` + `email`**（注册后**直接签发 token**，等同自动登录），前端 **`RentalAIAuth.persistSession`** 写入 `localStorage`，跳转 **`/`**。

## 4. Login Flow

- 页面 **`/login`**（`login.html`）→ **`POST /auth/login`**。
- 失败 → **`Invalid email or password.`**（401）。
- 成功 → **`token` + `user_id` + `email`**，写入 `localStorage`，跳转 **`/`**。

## 5. Session Handling

- **服务端**：内存字典 **`_AUTH_TOKENS[token] = user_id`**（与既有 Phase2/3 一致，非 JWT）。
- **客户端**：`localStorage`：`rentalai_bearer`、`rentalai_user_id`、`rentalai_user_email`。
- **`POST /auth/logout`**：删除服务端该 token；客户端 **`clearSession`** 并跳转 **`/login`**。
- **`GET /auth/me`**：校验 Bearer，返回公开资料；用于导航栏补全 email、以及检测**进程重启导致 token 失效**时清理本地状态。
- **导航**：`auth_session.js` 根据是否已登录渲染 **Login | Register** 或 **email + Logout**。

## 6. Data Binding

- **`POST /tasks`**、**`GET /tasks/{id}`**、**`POST /records/ui-history`**、**`GET /records/ui-history`** 仍通过 **`Authorization: Bearer`** → **`_get_user_id_from_request`**。
- 前端 **`RentalAIAuth.requireToken()`**：无 token 则拒绝发起上述请求。
- UI 保存快照时，服务端 **`insert_analysis_record(..., user_id=user_id)`** 不变，绑定当前登录用户。

## 7. History Isolation

- **`list_ui_history_records`** 仍为 **`WHERE user_id = ? AND analysis_type = p10_ui_history`**。
- 未登录访问 **`/history`**：列表请求失败，页面展示 **Please log in first**（含登录链接）。

## 8. Limitations

- Token 仅存**进程内存**，多 worker / 重启后全部失效，用户需重新登录。
- 密码仅为 **SHA-256**，无盐、无慢哈希，**不适合公网生产**。
- 无邮箱验证、无重置密码、无 OAuth。
- 旧版仅存 `rentalai_bearer` 的浏览器：首次加载会尝试 **`/auth/me`** 补全 email；若 401 会清空本地会话。

## 9. Next Step

- 持久化 session（Redis / DB）或多进程共享 token 表。
- 密码升级为 **bcrypt/argon2** + salt。
- 邮箱验证、忘记密码、账户设置页。
- 可选：短效 access + 长效 refresh（仍保持「简单」，不必完整 JWT 生态）。
