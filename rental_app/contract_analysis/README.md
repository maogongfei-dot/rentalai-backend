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
- **HTTP（Phase 4 最小）**：**`POST /api/contract/analysis/text`**（正文 + 可选 ``metadata``）、**`POST /api/contract/analysis/file-path`**（服务端本地路径，无上传）、**`POST /api/contract/analysis/upload`**（multipart ``file`` + 可选表单 ``metadata`` JSON 字符串；``.txt`` / ``.pdf`` / ``.docx``）。响应 ``result`` 为两层：**``summary_view``**（首屏绑定，字段来自 explain 核心切片）+ **``raw_analysis``**（完整 ``analysis_result`` / ``explain_result`` / ``presentation``）。

### Phase 4 网页（`/contract-analysis`）交接说明

| 项目 | 说明 |
|------|------|
| **用户主入口** | **粘贴文本**（``/api/contract/analysis/text``）与 **上传文件**（``.txt`` / ``.pdf`` / ``.docx`` → ``/api/contract/analysis/upload``）。 |
| **开发入口** | **服务端可读路径**（``/api/contract/analysis/file-path``）默认隐藏；页面底部「开发者：显示服务端路径」或首次访问 **`?dev=1`**（写入 localStorage 后去掉 query）后，在 **上传文件** 模式下显示 ``file_path`` 输入框；快捷「填入示例路径」亦仅在开发者模式下出现。 |
| **首屏展示块** | ``result.summary_view`` 七段：**总体结论**、**核心风险摘要**、**风险分类汇总**、**高亮风险条款**、**优先关注条款（条款严重度）**、**合同完整性**、**行动建议**（与页面 ``contract_analysis_page.js`` 渲染顺序一致）。 |
| **与包内能力对齐的限制** | **扫描版 PDF / 图片型 PDF** 无 OCR，抽字失败时分析可能为空或质量差；**规则与关键词为主**，不构成法律意见；**无 PDF 页码级定位**；复杂版式可能影响抽取。单文件上传默认约 **15 MB**（``RENTALAI_CONTRACT_UPLOAD_MAX_BYTES``）。 |

### Phase 4 第四轮：网页产品化展示（可演示，当前）

| 能力 | 说明 |
|------|------|
| **输入** | **粘贴文本**（JSON ``/api/contract/analysis/text``）与 **上传文件**（``.txt`` / ``.pdf`` / ``.docx`` → ``/api/contract/analysis/upload``）；开发用 **服务端路径** 见上表。 |
| **布局** | 宽屏双栏（输入 / 结果），窄屏上下堆叠；结果区空态与七段卡片分区清晰。 |
| **结果块** | ``summary_view`` 七段卡片：**总体结论**、**核心风险摘要**、**风险分类汇总**、**高亮风险条款**、**优先关注条款**、**合同完整性**、**行动建议**。 |
| **风险视觉** | 高/中/低徽标与色条；总体结论文本倾向（启发式）；分类与条款卡片分级展示。 |
| **可读性** | 条款摘录/位置预览 + ``<details>`` 全文；列表过长时「显示其余」；完整性长列表分段展开。 |
| **仍未做的增强** | **PDF 页码级定位**、**扫描件 OCR**、**LLM 条款解读**、与房源/聊天式入口等产品化整合、打印与导出等。 |

### Phase 5 首页入口（并列主能力）

- 首页 **`/`**（`web_public/index.html`）顶部 **「主功能」** 区为两张 **结构统一** 的并列卡片（`h3` 标题 + 英文副题 + 一行说明 + 底部同色 CTA）：**房源分析**（`#ai-rental-heading`）与 **合同分析**（`/contract-analysis`）。
- 顶部导航（`auth_local.js` → `renderUnifiedNav`）仍保留 **合同分析** 链接，与卡片二选一即可。

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

**multipart 上传**（字段名 ``file``；可选 ``metadata`` 为 JSON 字符串）：

```bash
curl -s -X POST "http://127.0.0.1:8000/api/contract/analysis/upload" ^
  -F "file=@contract_analysis/samples/sample_contract.txt;type=text/plain"
```

同一路径下另有 ``sample_contract.pdf``、``sample_contract.docx``（仓库内已提供），可替换 ``file=@…`` 分别验证 PDF / Word 上传解析。

**本地一键联调（推荐）**：在 ``rental_app`` 目录启动 API 后执行：

```bash
python scripts/contract_analysis_api_smoke.py
```

脚本会依次请求文本分析、文件路径、**三次 multipart**（txt / pdf / docx），并校验「不支持的扩展名」「空文件」返回 HTTP 400 与对应 ``error`` 码。

**手工用 curl 测三种格式**（需在 ``rental_app`` 根目录执行，路径按本仓库相对路径）：

```bash
curl -s -o /dev/null -w "%{http_code}\n" -X POST "http://127.0.0.1:8000/api/contract/analysis/upload" -F "file=@contract_analysis/samples/sample_contract.txt"
curl -s -o /dev/null -w "%{http_code}\n" -X POST "http://127.0.0.1:8000/api/contract/analysis/upload" -F "file=@contract_analysis/samples/sample_contract.pdf"
curl -s -o /dev/null -w "%{http_code}\n" -X POST "http://127.0.0.1:8000/api/contract/analysis/upload" -F "file=@contract_analysis/samples/sample_contract.docx"
```

成功时 HTTP 为 **200**，响应 JSON 中 ``ok: true``，且含 ``result.summary_view``。

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

浏览器打开 **`http://127.0.0.1:8000/contract-analysis`**（与 API 同源）。主流程：**「粘贴文本」** + **「上传文件」**；点 **「填入示例文本」** 可快速灌入样例。**服务端路径**与 **「填入示例路径（开发）」** 需先打开页面底部 **「开发者：显示服务端路径」**（或 **`?dev=1`**），并切换到 **上传文件** 模式后在表单中出现。示例数据见 `web_public/assets/contract_analysis_demo.js`（与 `samples/sample_contract.txt` 对齐）。

## 与 RentalAI 首页（Phase 4 第五轮）

RentalAI 以 **首页 `/`** 为统一入口，并列 **房源分析** 与 **合同分析** 两条主能力；本页为合同侧入口（与顶栏「合同分析」、首页主功能右卡一致）。全局产品结构、互通与「尚未落地」项见 **`rental_app/README.md`**「产品结构（Phase 4 第五轮）」。

## 尚未做的增强（非 Phase 3 范围）

- PDF **页码级**定位与复杂版式 **OCR**（含扫描件友好流程）。
- **LLM** 合同解读或条款生成。
- 与房源主流程的**深度合并**、**首页 / 聊天式入口**统一、结果**导出与打印**等（Phase 4 网页已具备可演示布局与交互，见「Phase 4 第四轮：网页产品化展示」）。
