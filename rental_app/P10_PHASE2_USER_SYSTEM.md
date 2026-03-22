# P10 Phase2 User System

---

## 1. User Model

新增 `users` 表（最小版）：

- `id`（uuid 字符串，主键）
- `email`（唯一）
- `password`（当前为 SHA-256 简单 hash）
- `created_at`

设计理由：

- 先满足“可注册 + 可登录 + 可绑定数据”的产品最小闭环；
- 不引入复杂认证依赖，保持可回退与低风险。

---

## 2. Auth Flow

### register

- `POST /auth/register`
- 输入：`email` + `password`
- 输出：`user_id`（成功时）

### login

- `POST /auth/login`
- 输入：`email` + `password`
- 输出：`user_id` + `token`

### token 使用

- 前端后续请求带：
  - `Authorization: Bearer <token>`

---

## 3. Token Strategy

- token 生成：`uuid4().hex`
- token 存储：服务进程内存 `token -> user_id` 映射
- token 验证：读取请求头 `Bearer`，查映射获取 `user_id`

局限性：

- 进程重启后 token 失效；
- 多实例不共享 token；
- 无过期时间与刷新机制。

---

## 4. Data Binding

### task 绑定 user

- `TaskRecord` 增加 `user_id`
- 创建 task 时写入 `user_id`
- 后续状态更新沿用同一 task 记录，自动保持归属

### analysis 绑定 user

- `analysis_records` 增加 `user_id`
- analysis 写入与缓存复用查询都带 `user_id`
- 避免跨用户误复用

---

## 5. API Impact

需要 user context 的接口：

- `POST /tasks`
- `GET /tasks`
- `GET /tasks/{task_id}`
- `GET /tasks/stats`
- `GET /tasks/system`
- `GET /records/tasks`
- `GET /records/tasks/{task_id}`
- `GET /records/analysis`
- `GET /records/properties`（当前需登录，但记录仍是全局）

查询限制：

- `tasks`/`analysis` 默认仅返回当前用户数据。

---

## 6. Frontend Integration

最小接入方式：在 Streamlit 侧栏加入登录块。

- 输入 email/password
- 调用 `/auth/register`、`/auth/login`
- 登录成功后将 token 存在 `st.session_state["auth_token"]`
- 异步任务与相关 API 请求自动带 `Authorization` 头

说明：

- 当前是 Streamlit 环境，未使用浏览器 `localStorage`，采用 session_state 的最小可用方案。

---

## 7. Limitations

当前安全性/功能限制：

- 无 JWT、无签名校验、无过期刷新；
- 无密码复杂度策略与重置流程；
- token 为内存态，重启即失效；
- `property_records` 暂未做 user 级绑定（仅保留登录访问门槛）。

为什么可以接受：

- 当前阶段目标是“用户归属基础能力”，不是生产级安全体系；
- 方案改动小、可快速迭代升级。

---

## 8. Recommended Next Step

建议进入：**P10 Phase2 - Step2《用户历史页最小版 + token 持久化增强》**。

优先项：

1. 增加“我的任务/我的分析”只读历史视图；
2. token 增加最小 TTL 与失效提示；
3. 评估迁移到 JWT（保持接口兼容）。
