# 合同分析模块（Phase 3）— 最小开发说明

> 验收脚本：`python -m contract_analysis.phase3_acceptance` · 更细的字段清单见 `PHASE3_ACCEPTANCE.md`。

## 输入

| 方式 | 说明 |
|------|------|
| **内存文本** | `contract_text: str`（粘贴、或已由上游抽取的字符串） |
| **文件路径** | `.txt` / `.pdf` / `.docx` → `contract_document_reader` 抽文本后再走同一分析管线 |

`ContractInput.source_type` / `source_name` 写入 `structured_analysis.meta`，便于审计与 UI 展示来源。

## 核心输出（稳定形状）

一次完整调用（推荐 **`analyze_contract_with_explain`**）返回：

- **`structured_analysis`**：`summary`、`risks`、`missing_items`、`recommendations`、`detected_topics`、`clause_list`、`clause_risk_map`、`clause_severity_summary`、`contract_completeness`、`risk_category_summary`、`risk_category_groups`、`meta`（list 字段不为 `None`，见 `contract_models`）。
- **`explain`**：人话层 + 卡片字段（含 `highlighted_risk_clauses`、`clause_*_overview`、`contract_completeness_overview` 等）。
- **`presentation`**：`sections`（`kind` + `items`/`text`）+ `plain_text`，便于直接绑前端。

仅要规则层时可调 **`analyze_contract`**（同包，无 explain/presentation）。

## 已支持能力（当前版本）

- **风险识别**：关键词 / 轻量规则（含押金数值、主题不合理表述等），非 LLM。
- **条款切分**：`clause_list` + `clause_type` / `matched_keywords`。
- **风险分类**：`risk_category`、汇总与分组（`risk_category_summary` / `risk_category_groups`）。
- **条款—风险联动**：`clause_risk_map`；Explain 侧 **`clause_risk_overview`**。
- **条款风险强度**：`clause_severity_summary`；Explain 侧 **`clause_severity_overview`**（Top risky clauses）。
- **合同完整性检查**：`contract_completeness`；Explain 侧 **`contract_completeness_overview`**（单卡）。

## 已知限制

- **规则以关键词与启发式为主**，输出不构成法律意见。
- **无 PDF 页码级定位**；`location_hint` 多为句级/窗口描述，复杂版式或扫描件抽字可能失败。
- 完整性分数为 **清单关键词命中** 的启发式，与真实法务审查不等价。

---

## Phase 4 接入建议（最小）

- **优先**：在前端做 **上传 / 粘贴** → 调 **`POST /api/contract/phase3/analyze-text`**（已有），或后端增加 **multipart 上传** 抽文本后转同一入口；UI 直接消费 **`result.presentation.sections`** 与 **`explain`** 稳定字段。
- **Python 侧首选复用入口**：**`contract_analysis.service.analyze_contract_with_explain`**（文件则用 **`analyze_contract_file_with_explain`**）。与 HTTP 层一致，便于单测与任务队列封装。
