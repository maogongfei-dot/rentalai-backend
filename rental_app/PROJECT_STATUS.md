# RentalAI — 项目状态（v1）

## 已完成的模块

- **Phase 5 第三轮 · 后端 JSON 用户与历史数据基础（阶段完成）**：用户 **`persistence_users.json`**（`/auth/register`、`/login`、`/me`）；分析历史 **`persistence_analysis_history.json`**（房源/合同成功后可写；**`GET /api/analysis/history/records`** 可读）。详见 **`rental_app/persistence/README.md`**、主 **`README.md`**「Phase 5 第三轮」。
- **Phase 5 第二轮 · 最小用户账户体验（阶段完成）**：顶栏 **Login / Sign Up**、已登录 **邮箱 + Logout**、**`/account`**；`RentalAIUserStore`；浏览器内历史按 **`guest` / `userId` 分桶**；访客提示不强制登录。
- **本地假登录 / 邮箱登录**：`/login`（本地演示 `current_user` 或邮箱 Bearer），受保护页统一顶栏导航。
- **AI 一句话分析**：`POST /api/ai-analyze` → 结果页展示结构化需求、推荐列表。
- **Explain/风险/决策**：解释文案、优缺点、风险提示、租/慎/不建议。
- **收藏与对比**：按 `user_id` 隔离的 `fav_list_*`，`/compare` 对比收藏与当前会话推荐。
- **分析历史（浏览器）**：统一摘要 **`localStorage`** + 手动保存列表；**服务端 JSON 历史与之并行**，尚未完全切换。
- **Demo 收口**：首页使用说明、结果页操作区、清空本地测试数据（开发用）。

## 当前阶段

**Demo / MVP 可用**：后端已具备 **可落盘**用户与历史 JSON；**不是**生产级多租户 SaaS。

## 尚未做的内容（已知）

- **生产级账号**：邮箱验证、密码策略（当前为 **SHA-256 演示哈希**）、HttpOnly 会话、刷新令牌、按用户的服务端权限模型。
- **受保护 API**：多数分析/历史接口仍**不**强制 Bearer；历史 **`userId`** 查询可伪造（Demo 可接受）。
- **前端全面云端历史**：分析历史页默认仍读 **localStorage**；与服务端记录合并/去重未做。
- **数据库迁移**：用户与历史由 **JSON** 承载，未迁 **PostgreSQL/SQLite** 业务表。
- 正式部署上的安全加固、审计与监控（除已有文档与可选 Webhook）。
- 多平台房源数据与抓取策略的规模化与合规流程。

## 下一阶段建议

1. **产品优先**：**分析历史页读取并展示 `GET /api/analysis/history/records`**（与本地列表并存或开关），并把请求 **`userId`** 与登录用户对齐。
2. **安全优先**：**Bearer 校验** + 历史接口仅允许访问**当前 token 对应 userId**（或 guest 桶策略）。
3. **数据优先**：需要审计/多实例时再 **数据库升级**（用户表 + 历史表），并规划从 JSON 迁移。
