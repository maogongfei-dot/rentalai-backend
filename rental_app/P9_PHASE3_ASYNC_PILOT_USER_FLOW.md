# P9 Phase3 Async Pilot User Flow

---

## Entry

用户在侧栏 **Real listings (P7)** 区勾选 **Async mode (pilot)** checkbox，然后在 batch expander 中点击 **"Run real multi-source analysis (async)"** 按钮。

---

## Step 1 — Create Task

前端调用 `POST {api_base}/tasks`，发送：

```json
{
  "sources": ["rightmove", "zoopla"],
  "limit_per_source": 8,
  "budget": 1500.0,
  "target_postcode": "SW1A",
  "headless": true,
  "persist": true
}
```

页面显示：`Submitting async task to backend…`

---

## Step 2 — Receive task_id

服务端返回：

```json
{ "task_id": "a1b2c3d4e5f6", "status": "queued" }
```

页面更新：`Task a1b2c3d4e5f6 — queued`

---

## Step 3 — Poll Status

前端每 3 秒请求 `GET {api_base}/tasks/a1b2c3d4e5f6`。

页面依次显示：
- `Task a1b2c3d4e5f6 — running`
- （等待 30–120 秒）

---

## Step 4 — Display Result

任务完成后，前端收到 `status: success`（或 `degraded` / `failed`）。

- **成功 / 降级**：`result` 字段包含完整 `analysis_envelope`，前端将其写入 `st.session_state["p2_batch_last"]` 并 rerun。批量分析结果页（listing 卡片、filter/sort、Agent insight）正常渲染。
- **失败**：页面显示错误信息。

---

## Notes

- 当前是试点版 — 仅 batch expander 中的按钮支持 async，Agent 入口仍走同步。
- 旧同步流程仍然保留 — 取消勾选 **Async mode (pilot)** 即恢复旧行为。
- 同一时刻最多运行 1 个分析任务（`Semaphore(1)`），多余提交立即返回 "Server busy"。
