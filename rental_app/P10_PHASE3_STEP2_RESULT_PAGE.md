# P10 Phase3 Step2 Result Page

## 1. Goal

在 **Phase3 Step1** 已跑通「首页 → 异步任务 → 结果页」的基础上，将 **`/result/{task_id}`** 整理为**最小可用、用户可读**的产品页：分区展示结论、房源、Explain 与风险信息；兼容字段缺失与多种后端结构；避免把原始 JSON 直接堆给用户；并在底部提供**默认折叠**的 Debug 区域便于排查。

## 2. Page Sections

| 区块 | 说明 |
|------|------|
| **Result header** | Recommendation（由 `decision_code` 等映射为 Recommended / Not Recommended / Caution / N/A）、Final score、`task_id`（小字 code）、分析状态（completed / completed (degraded) / failed）、可选 elapsed |
| **Property overview** | Title、rent/price、postcode/location、bedrooms、bills（Included/Not included）、listing URL；无数据则整块隐藏 |
| **Explain summary** | Summary 段落；Pros / Cons 分栏列表（数组或字符串均先规范为列表） |
| **Risk flags** | `risk_flags` 列表；若有 `decision.risk_signal` / `risk_level` 则显示 Severity；`next_steps` 等作为 Suggested next steps；若无显著风险信号则文案 **No major risk flags detected**（仍可单独展示 next steps） |
| **Raw / debug** | `<details>` 默认折叠，内为完整 **GET /tasks/{id}** JSON（`JSON.stringify`） |

加载中与失败使用独立面板：**Analyzing…**（含状态提示）、**Analysis failed**（含精简 error）。

## 3. Data Mapping

适配层位于 **`web_public/assets/result_view_model.js`** 的 **`buildResultViewModel(taskState)`**，优先顺序概览：

| 展示字段 | 主要来源 | 回退 |
|----------|----------|------|
| Final score | `representative_row.score` | `final_score`、`property_score` |
| Recommendation | `decision_code` | `decision_label`、`decision_summary` 关键词粗判 |
| Summary | `p10_explain.explain_summary` | `decision_summary`、`decision_label` |
| Pros | `p10_explain.pros` | `recommended_reasons` |
| Cons | `p10_explain.cons` | `concerns` |
| Risk flags | `p10_explain.risk_flags` | `risks`（batch enrich） |
| Severity | `decision.risk_signal` | `decision.risk_level` |
| Next steps | `next_steps` | `analysis.recommended_inputs_to_improve_decision`、`required_actions_before_proceeding` |
| Title / rent / postcode / bedrooms / bills / URL | `input_meta.*` | 行级兼容字段 |

**不修改** Python 分析引擎；仅在前端做轻量归一与展示。

## 4. Empty State Handling

- 缺失、`null`、空字符串、空数组：对应 **Property** 行**整行隐藏**（不强行显示 N/A 占位，除非 Explain 的 summary 全无则显示 **N/A**）。
- Pros / Cons 列表为空时列表内显示 **N/A**（muted）。
- 无任何 property 字段时隐藏 **Property overview** 整块。

## 5. Failed State Handling

- `task.status` 为 `failed` / `timeout` / `interrupted`：展示 **Analysis failed**、**Please try again.**，以及 **Detail**（`error` 截断约 280 字符）。
- 轮询超时、网络错误、404（如换浏览器导致无权限）：同样进入失败面板，Detail 为简短原因（如 task not found）。
- 底部 Debug 仍可展开查看当时能拿到的 `raw_task_state`。

## 6. In-Progress Handling

- 任务为 `queued` / `running` 等：保持 **Analyzing…** 面板，**`#loading-status`** 更新为含当前 `status` 的说明文案。
- 继续轮询，**不抛未捕获异常**；完成后切换到结果或失败面板。

## 7. View Model

**`buildResultViewModel(taskState)`** 返回：

```text
{
  phase: "loading" | "ready" | "failed",
  errorMessage?: string,
  display_payload: {
    version: 1,
    task_id, task_status,
    header: { verdict_key, verdict_label, final_score, analysis_status, degraded },
    property: { title, price, postcode, bedrooms, bills, listingUrl },
    explain: { summary, pros[], cons[] },
    risk: { risk_flags[], severity, next_steps[], show_no_flags_message },
    meta: { elapsed_seconds, stage, batch_row_index }
  },
  raw_task_state: <原始 API 响应>
}
```

渲染成功后 **`window.__rentalaiLastDisplayPayload`** 指向 **`display_payload`**，便于下一步「保存分析记录 / 用户历史」直接提交或序列化。

## 8. Limitations

- 仍为**静态页 + 轮询**，无实时进度百分比。
- Recommendation 依赖 batch 行上的 **`decision_code`** 等；若引擎未产出，可能长期为 **N/A**。
- **Severity** 仅映射少量 `decision` 字段；未接入完整 Module3 structured 视图。
- Debug JSON 可能很大，仅适合开发排查。
- 多房源仅展示 **representative** 一行对应的 property 摘要（与 P10 explain 一致）。

## 9. Next Step

- 用 **`display_payload`** 对接 **POST** 保存分析快照或写入用户历史 API。
- 在结果页增加「**全部 batch 摘要表**」（只读），仍复用同一 task `result`。
- 将轮询改为 SSE/WebSocket 或暴露可取消任务。
- 与登录态打通：显式账号与 guest 策略说明。
