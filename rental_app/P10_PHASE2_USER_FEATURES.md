# P10 Phase2 User Features

---

## 1. User History

**实现方式**

- 任务历史：复用 SQLite 镜像表 `task_records`，经 `GET /records/tasks` 按 `user_id` 过滤。
- 分析历史：复用 `analysis_records`，经 `GET /records/analysis` 按 `user_id` 过滤。

**接口**

- `GET /records/tasks` — 最近任务（`ORDER BY updated_at DESC`，最新优先）。
- `GET /records/analysis` — 最近分析记录（`ORDER BY id DESC`）。

**前端**

- Streamlit 侧栏 expander「Load history / saved list」中点击 **Refresh task + analysis history**，表格展示最近记录（需已登录且非 local-only 模式）。

---

## 2. Favorites System

**数据模型（`favorite_records`）**

| 字段 | 说明 |
|------|------|
| `id` | 主键（uuid 字符串） |
| `user_id` | 归属用户 |
| `listing_url` | 可选，房源链接（与 `property_id` 至少填其一） |
| `property_id` | 可选，稳定 id（无 URL 时用，如 `batch_row_{index}`） |
| `title` | 标题摘要 |
| `price` | 月租等数值 |
| `postcode` | 邮编 |
| `created_at` | 创建时间 |

**最小去重**

- `(user_id, listing_url)` 唯一（`listing_url` 非空时）。
- `(user_id, property_id)` 唯一（`property_id` 非空时）。

**API**

- `POST /favorites` — 添加收藏（body 含 `listing_url` 和/或 `property_id` 及 `title` / `price` / `postcode`）。
- `GET /favorites` — 当前用户收藏列表（`created_at` 降序）。
- `DELETE /favorites/{id}` — 删除（仅本人）。

**使用**

- 登录后，在 Batch 结果区选择行 → **Add selected to favorites**。
- 侧栏可 **Load my favorites**，并可通过 id 删除。

---

## 3. Compare Feature

**输入 / 输出**

- `POST /compare`，body：`{ "properties": [ {...}, {...}, ... ] }`，**2–5** 条（MVP 前端固定选 2 条）。
- 每条为 **analyze-batch 结果行** 结构（含 `input_meta`、`score` 等）。
- 返回 `comparison.items`：每条的 `price`、`bedrooms`、`commute_minutes`、`postcode`、`score`、`decision_code` 等摘要字段；`comparison.summary` 标出 **最高分**、**最低价** 所在 slot。

**与 analysis 的关系**

- 不重新跑引擎；只从已分析结果行中抽取字段做并列对比，零额外成本、低风险。

---

## 4. Frontend Integration

| 位置 | 行为 |
|------|------|
| 侧栏 **P10 · History & favorites** | 刷新任务/分析历史；加载收藏列表；按 id 删除收藏 |
| Batch 结果下方 **P10 · Favorites & compare** | 多选 → 加入收藏；两个下拉框选 A/B → **Run compare** |

**用户操作路径**

1. 登录（侧栏 User）。
2. 跑多平台 batch，得到结果列表。
3. 选收藏 → 添加；或选两项 → 对比。
4. 在侧栏查看历史与收藏列表。

---

## 5. Why This Is Core Product Value

- **历史**：用户能“看到自己做过的分析”，从工具变成可回顾的产品。
- **收藏**：把“感兴趣的房源”从一次性列表变成可管理的清单。
- **对比**：在 2 个选项间做结构化决策，是租赁场景的核心心智。

---

## 6. Limitations

- UI 极简，无独立路由页（仅侧栏 + batch 下方区块）。
- 收藏与对比依赖 **已登录 + API**；local 引擎模式不可用。
- `property_records` 仍未按用户归属；全局房源记录未与收藏强关联。
- Compare 不重新计算分数，仅展示已有结果字段。

---

## 7. Recommended Next Step

**建议进入：P10 Phase2 - Step3《收藏与对比体验增强 + 数据一致性》**

- 收藏与 `property_records` 可选关联（同一 `listing_url`）。
- Compare 支持 3–5 条的小表格视图（仍保持简单）。
- Token 持久化 / 会话提示，减少“未登录”误操作。
