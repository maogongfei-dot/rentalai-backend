# 合同分析模块（Phase 3）— 最小开发说明

> 验收脚本：`python -m contract_analysis.phase3_acceptance` · 更细的字段清单见 `PHASE3_ACCEPTANCE.md`。

## 模块结构（核心文件）

| 文件 | 职责 |
|------|------|
| `contract_models.py` | TypedDict / 输入输出形状、coerce 函数 |
| `contract_rules.py` | 风险规则、主题、完整性清单、`match_clause_type_from_text` |
| `contract_analyzer.py` | 主分析：`analyze_contract_text(ContractInput)`、条款图、完整性 |
| `contract_explainer.py` | `explain_contract_analysis`（人话层） |
| `contract_document_reader.py` | txt / pdf / docx 抽取 |
| `contract_clause_split.py` | 条款切分 |
| `presentation.py` | CLI 报告、`build_contract_presentation` |
| `service.py` | **推荐业务入口**：`analyze_contract*`、`build_contract_input_from_file` |
| `entrypoints.py` | 与 `service`+`explainer`+`analyze_contract_text` 的**聚合导出**（无额外逻辑） |
| `sample_contracts_data.py` + `samples/` | 内置样例正文 |
| `demo_*.py`、`phase3_acceptance.py` | 演示与总验收 |

## 推荐复用入口（Python）

| 场景 | 函数 | 说明 |
|------|------|------|
| 完整三层（结构化 + explain + presentation） | `analyze_contract_with_explain` | **首选**；同 `service` 与 `entrypoints` |
| 仅第一层 | `analyze_contract` | 等价于便捷封装后的 `analyze_contract_text` |
| 低层 API | `analyze_contract_text` | 参数为 `ContractInput`（见 `contract_analyzer`） |
| 文件路径 | `analyze_contract_file` / `analyze_contract_file_with_explain` | 先抽取再分析 |
| 仅 explain | `explain_contract_analysis` | 入参为结构化 dict；一般由管线自动调用 |

聚合导入：`from contract_analysis.entrypoints import analyze_contract_with_explain, ...`  
包级导入：`from contract_analysis import analyze_contract_with_explain`（与上等价，符号更多）。

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

- **正式门面（推荐）**：仓库根 **`contract_analysis_service.py`** 提供 **`analyze_contract_text`** / **`analyze_contract_file`**，统一返回 **`analysis_result`**、**`explain_result`**、**`presentation`**（内部仍调用 ``contract_analysis.service``，不重复实现规则）。
- **HTTP（Phase 4 最小）**：**`POST /api/contract/analysis/text`**（正文 + 可选 ``metadata``）、**`POST /api/contract/analysis/file-path`**（服务端本地路径，无上传）。响应 ``result`` 为两层：**``summary_view``**（首屏绑定，字段来自 explain 核心切片）+ **``raw_analysis``**（完整 ``analysis_result`` / ``explain_result`` / ``presentation``）。
- **HTTP（Phase 3 兼容）**：**`POST /api/contract/phase3/analyze-text`** 由门面组装 ``result``，并保留 ``structured_analysis`` / ``explain`` 旧键名。
- **包内等价**：**`contract_analysis.service.analyze_contract_with_explain`** / **`entrypoints`** 与门面数据一致，仅键名不同（``structured_analysis`` vs ``analysis_result``）。

## 本地测试合同分析接口（Phase 4 HTTP）

前提：在 **`rental_app`** 目录启动 API：`python run.py`（默认 `http://127.0.0.1:8000`）。

### 方式一：项目内脚本（推荐）

```bash
cd rental_app
python scripts/contract_analysis_api_smoke.py
```

可选：`set RENTALAI_API_BASE=http://127.0.0.1:8000`（或其它部署地址）。

### 方式二：curl

**文本**（PowerShell 可将单引号改为双引号并转义内层引号）：

```bash
curl -s -X POST "http://127.0.0.1:8000/api/contract/analysis/text" ^
  -H "Content-Type: application/json" ^
  -d "{\"contract_text\":\"Monthly rent 500 pcm. Deposit 500.\",\"metadata\":{\"source_name\":\"curl-test\"}}"
```

**文件路径**（相对 `rental_app` 根）：

```bash
curl -s -X POST "http://127.0.0.1:8000/api/contract/analysis/file-path" ^
  -H "Content-Type: application/json" ^
  -d "{\"file_path\":\"contract_analysis/samples/sample_contract.txt\"}"
```

### 方式三：Python requests

```python
import requests
r = requests.post(
    "http://127.0.0.1:8000/api/contract/analysis/text",
    json={"contract_text": "Rent 1 pcm.", "metadata": {"source_name": "py"}},
    timeout=60,
)
print(r.status_code, r.json().get("ok"), list((r.json().get("result") or {}).keys()))
```

成功时 `result` 含 **`summary_view`**（至少含 `overall_conclusion`、`key_risk_summary`、`risk_category_summary`、`highlighted_risk_clauses`、`clause_severity_overview`、`contract_completeness_overview`、`action_advice`）与 **`raw_analysis`**（上述三门面数据的完整副本）。

### 方式四：浏览器页面（联调）

浏览器打开 **`http://127.0.0.1:8000/contract-analysis`**（与 API 同源）。表单上方有 **「填入示例文本」**、**「填入示例路径（文件模式）」**，再点 **提交分析**，可快速验证文本与文件路径两条流程；示例数据见 `web_public/assets/contract_analysis_demo.js`（与 `samples/sample_contract.txt` 对齐）。

## 尚未做的增强（非 Phase 3 范围）

- PDF **页码级**定位与复杂版式 OCR。
- **LLM** 合同解读或条款生成。
- 专用 **multipart** Phase 3 路由（当前可先抽文本再调现有 API）。
- 与房源主流程的**深度合并**（当前子模块独立可测）。
