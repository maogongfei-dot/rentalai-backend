# P10 Phase2 Explain Engine

---

## 1. Why Explain Matters

租赁决策依赖 **价格、通勤、账单、户型、区域** 等多维信息。仅有 `final_score` 数字时，用户难以理解「为什么推荐 / 为什么不推荐」。  
Explain Engine 把 **与模块评分一致的维度分数** 转成 **可读摘要、优缺点与风险提示**，是 RentalAI 相对「黑盒打分」的 **核心产品差异**。

---

## 2. Input Data

Explain **不调用大模型**，输入为：

| 来源 | 内容 |
|------|------|
| `top_house_export.scores`（或行内 `scores`） | `price_score`、`commute_score`、`bills_score`、`bedrooms_score`、`area_score`（0–100，与 `module2_scoring` 一致） |
| `score` | 综合分（用于一句话强弱修饰） |
| `input_meta` | `bills_included`、`postcode` / `area` 等（用于风险规则） |
| `decision_code` | `recommended` / `not_recommended` 等（用于额外风险提示） |

**多源任务级汇总**：`build_p10_explain_from_msa_result` 取 **本轮 batch 中分数最高的成功行** 作为代表，生成写入 `analysis_records` 的汇总 explain。

---

## 3. Rule Design

与 `module2_scoring` 中 listing explain 阈值对齐：

- 单维度 **≥ 80**：记为 **优点**（对应维度一条中文 pro）
- 单维度 **≤ 50**：记为 **缺点**（对应维度一条中文 con）
- 每类最多 **3** 条，避免刷屏

**风险规则（示例）**：

- `bills_included == False` → 额外账单风险提示  
- 区域分低且填写了 postcode → 建议核实治安与配套  
- 价格/通勤维度弱 → 预算或通勤风险  
- `decision_code == not_recommended` → 综合谨慎提示  

**一句话 summary**：由 pros/cons 有无与 `score` 档位组合生成（中文）。

---

## 4. Output Structure

```json
{
  "explain_summary": "string",
  "pros": ["..."],
  "cons": ["..."],
  "risk_flags": ["..."],
  "dimensions": { "price": 82.0, "commute": 45.0 }
}
```

- **DB**：`analysis_records` 增加列 `explain_summary`、`pros`、`cons`、`risk_flags`（列表存 JSON 文本）。
- **JSON**：`result_summary.p10_explain` 同步一份，便于只读 `result_summary` 的客户端。

---

## 5. Integration Points

| 位置 | 行为 |
|------|------|
| `api_server._run_analysis_task` | 多源分析成功 / 缓存命中 / 失败 时调用 `insert_analysis_record`，写入 explain 字段与 `p10_explain` |
| `GET /records/analysis` | 经 `records_query_service` 返回 `explain_summary` / `pros` / `cons` / `risk_flags` |
| `POST /compare` | 每个 `comparison.items[]` 增加 `explain`（对应该条 batch 行） |
| `app_web.py` | Batch 结果下方 **P10 · 推荐理由** 展开；对比结果中 **Compare — explain 摘要** |

---

## 6. Example Outputs

**示例 A（价格、通勤双高）**

```json
{
  "explain_summary": "综合分较高。整体表现偏积极：租金维度得分较高，价格相对更有竞争力。",
  "pros": ["租金维度得分较高，价格相对更有竞争力", "通勤维度得分较高，通勤时间相对更理想"],
  "cons": [],
  "risk_flags": []
}
```

**示例 B（账单未包 + 区域分低）**

```json
{
  "explain_summary": "该房源在「租金维度得分较高…」方面较有优势，但「区域/地段匹配度一般」需留意。",
  "pros": ["租金维度得分较高，价格相对更有竞争力"],
  "cons": ["区域/地段匹配度一般"],
  "risk_flags": [
    "未勾选包账单：可能存在水电煤等额外支出，需自行核实。",
    "区域匹配得分偏低：建议结合治安、交通与生活配套自行核实。"
  ]
}
```

**示例 C（分析失败占位）**

```json
{
  "explain_summary": "该条分析未成功，暂无法生成推荐理由。",
  "pros": [],
  "cons": [],
  "risk_flags": ["分析失败或数据不足，请重试或调整条件。"]
}
```

---

## 7. Limitations

- 规则固定，**无法覆盖所有个体语境**（如具体街区口碑）。
- 强依赖 **batch 行是否带齐 `top_house_export.scores`**；缺失维度则该维不参与 pros/cons。
- 与现有 `engines/explain_engine.py`（Module7 长链路）**并行存在**；P10 侧重 **产品向中文短句**，不替换引擎内部决策协议。

---

## 8. Recommended Next Step

**建议进入：P10 Phase2 - Step4《Explain 与 Module7 / 统一决策文案对齐》**

- 可选将 P10 摘要 **附加** 到 `unified_decision_payload` 的只读字段（仍规则驱动）。
- 增加 **单元测试**（固定分数矩阵 → 固定中文输出）。
- 按真实用户反馈 **微调阈值与文案**，仍保持无 LLM。
