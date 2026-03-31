# Phase 3 合同分析模块 · 总验收说明

开发与 Phase 4 接入（精简）：见同目录 **`README.md`**。

## 入口

| 用途 | 命令 / 调用 |
|------|-------------|
| **总验收（本页）** | `python -m contract_analysis.phase3_acceptance` 或 `test_phase3_acceptance()` |
| 全量样例断言 | `python -m contract_analysis.demo_contract_samples`（内部 `test_contract_analysis_samples`） |
| 固定 `sample_contract.*` 读文件 + 分析 | `python -m contract_analysis.demo_contract_document_readers` |
| 文件分析别名 | `python -m contract_analysis.demo_contract_file_analysis` |

## 已覆盖的输入类型

| 类型 | 验证方式 |
|------|----------|
| 直接文本 | `analyze_contract_with_explain(contract_text=...)`（`PHASE3_TEXT_SCENARIOS` + 边界用例） |
| `.txt` 文件 | `analyze_contract_file_with_explain` → `samples/sample_contract.txt` |
| `.pdf` 文件 | 同上 → `samples/sample_contract.pdf`（若文件存在） |
| `.docx` 文件 | 同上 → `samples/sample_contract.docx`（若文件存在） |

缺二进制样例时可运行 `python scripts/generate_sample_contract_documents.py`（仓库约定）。

## 已覆盖的风险 / 业务场景（总验收文本矩阵）

| 场景 | 样例来源（常量 / 文件） |
|------|-------------------------|
| 安全 / 低风险 | `SAMPLE_CONTRACT_SAFE` |
| 中等风险 | `SAMPLE_CONTRACT_MEDIUM_RISK` |
| 高风险 | `SAMPLE_CONTRACT_HIGH_RISK` |
| 隐藏费用 / 罚金 | `SAMPLE_CONTRACT_HIDDEN_FEES_PENALTY` |
| 房东进入权 / 未合理通知 | `SAMPLE_CONTRACT_UNFAIR_ENTRY` + `SAMPLE_LOC_LANDLORD_ACCESS`（长文 + 定位短样） |
| 租客承担全部维修 | `SAMPLE_LOC_TENANT_REPAIRS` |
| 缺通知期 / 缺维修（完整性） | `SAMPLE_COMPLETENESS_MISSING_NOTICE_REPAIR` |
| 极短不完整合同 | `SAMPLE_COMPLETENESS_SHORT_INCOMPLETE` |
| 边界：空正文、无规则命中 | 内联短文本 |

## 总验收检查项

- 主流程：`analyze_contract_with_explain` / `analyze_contract_file_with_explain` 可跑通。
- **structured_analysis**：`PHASE3_STRUCTURED_REQUIRED_KEYS` 齐全；`risks` 等 list 不为 `None`；`contract_completeness` 含 `missing_core_items` / `unclear_items` 等稳定结构。
- **explain**：`PHASE3_EXPLAIN_REQUIRED_KEYS` 齐全；`highlighted_risk_clauses` 等 list 不为 `None`；`contract_completeness_overview` 为 dict。
- **无命中 / 空输入**：返回空 list 与默认结构，不抛异常。

## 已知限制（非阻塞 MVP）

- **PDF**：依赖抽取文本质量；复杂版式/扫描件可能抽字失败；**无 PDF 页码级定位**（仍为文本窗口 / 句级 `location_hint`）。
- **DOCX**：依赖段落抽取；宏或极端格式未专项覆盖。
- **规则引擎**：关键词与轻量规则，**不构成法律意见**；未接 LLM 解读。
- **完整性分数**：基于关键词强/弱命中启发式，与真实法务审查不等价。

## MVP 结论

在通过 `phase3_acceptance` 与 `test_contract_analysis_samples` 的前提下，本模块可作为 **RentalAI MVP 的正式合同分析子模块** 使用；前端与 API 可依赖稳定字段（见 `contract_models` 与 `_normalize_*` 注释）。
