# P8 Phase2 Integration Status

本文档对应 **Phase2 Step3**，基于代码审查确认前端 → 后端 → 分析桥 → 抓取的整站联调状态。

---

## 1. Frontend → Backend

**状态：Pass（有条件）**

### 通过项

- `app_web.py` 第 593 行的 API base URL 来自 `os.environ.get("RENTALAI_API_URL", "http://127.0.0.1:8000")`，部署时通过环境变量切换到公网地址即可，无需改代码。
- Step2 已将侧栏帮助文案改为环境变量感知：公网 URL 时不再显示本地启动提示。
- HTTP 请求路径（`/analyze`、`/analyze-batch`、`/score-breakdown`、`/risk-check`、`/explain-only`）与 `api_server.py` 路由完全一致，无前缀差异。
- `RENTALAI_USE_LOCAL=1`（`render.yaml` 默认）时，单条 Analyze / Agent / 真实抓取走进程内引擎，**不依赖 API URL**——即使 API 服务暂未上线，UI 核心功能仍可用。

### 风险项

- 关闭 `Use local engine` 后，batch JSON 请求会打到 `RENTALAI_API_URL`。若该变量未配置或 API 服务休眠，用户会看到请求失败提示（非崩溃）。
- CORS 当前为 `allow_origins=["*"]`——演示可用，生产需收紧。

### 残留 localhost 引用

`app_web.py` 中的 `http://127.0.0.1:8000` 出现在：

- **fallback 默认值**（env 未设置时）：合理行为，不影响配置正确的部署。
- **help 文案**（`"Local: http://127.0.0.1:8000"`）：仅界面提示文字，非请求目标。
- **文件头注释**（`# 浏览器: http://localhost:8501`）：开发备注，无运行时影响。

结论：**无需额外代码修改**。

---

## 2. Backend → Analysis Bridge

**状态：Pass**

### 通过项

- FastAPI 的 `/analyze` 和 `/analyze-batch` 调用 `api_analysis.py` 中的 `modular_analyze_response` / `analyze_batch_request_body`，完全在 Python 进程内完成，不依赖文件系统或 Playwright。
- `api_server.py` 不 import 任何 `data.scraper.*` 或 `data.pipeline.*`，与抓取模块无耦合。
- `listing_storage.py` 路径使用 `Path(__file__).resolve().parent` 基准 + `RENTALAI_LISTINGS_PATH` 环境变量覆盖，无硬编码绝对路径。

### 风险项

- `area_module.py` 使用 `open("area_data.json")` 相对路径（依赖 cwd = `rental_app`）。`render.yaml` 的 `rootDir: rental_app` 和 `startCommand` 均在该目录下执行，路径可解析。但如果工作目录被外部修改，会静默异常。属 Low 风险。

---

## 3. Backend → Scraper

**状态：Pass（不适用：后端不直接调用 Scraper）**

### 架构说明

FastAPI 后端 **不** 调用抓取模块。抓取由 Streamlit 进程内触发（`real_analysis_service.py` → `analysis_bridge.py` → `multi_source_pipeline.py` → `playwright_runner.py`）。

因此 "Backend → Scraper" 不是一条部署联调路径。需要关注的是 **Frontend (Streamlit) → Scraper**：

| 检查项 | 结果 |
|--------|------|
| 调用方式 | 同步、进程内 |
| Playwright 安装 | `buildCommand` 含 `playwright install chromium` |
| 浏览器二进制 | build 阶段下载，运行时调用 |
| 本地文件依赖 | Debug 样本输出到 `samples/debug/`（可写失败时静默跳过） |
| 系统环境 | 需 Chromium 系统库（Render Python 运行时不保证完整） |

### 风险项

- **High**：Playwright Chromium 系统库缺失导致 UI 服务 build 失败。
- **Medium**：Rightmove/Zoopla 反爬在云 IP 上更激进。
- **Medium**：同步抓取阻塞 Streamlit，其他用户操作排队等待。

---

## 4. Current End-to-End Readiness

**整站已接近可上线状态。**

| 路径 | 状态 | 说明 |
|------|------|------|
| UI 首页加载 | Ready | Streamlit 无 build 产物，启动即服务 |
| 单条 Analyze（进程内） | Ready | `RENTALAI_USE_LOCAL=1`，不依赖 API |
| 单条 Analyze（HTTP） | Ready | 需 API 服务在线 + `RENTALAI_API_URL` 配置 |
| Batch JSON（HTTP） | Ready | 同上 |
| Agent Parse → Intent | Ready | 纯 Python 逻辑，无外部依赖 |
| Agent → 真实抓取 + 分析 | Conditional | 取决于 Playwright build 成功 + 目标站可达 |
| Health Check（API） | Ready | `GET /health` → `{"status":"ok"}` |
| Health Check（UI） | Ready | `GET /` → Streamlit 首页 |

### 还差什么

1. **一次真实 build 验证**：Playwright Chromium 在 Render 上是否能成功安装。
2. **一次端到端触发**：在线上环境从 Agent 触发抓取 → 分析 → 结果展示。
3. **`RENTALAI_API_URL` 配置**：UI 服务部署后需手动填写 API 公网地址。

---

## 5. Remaining Blocking Issues

| 优先级 | 问题 | 影响范围 |
|--------|------|----------|
| **High** | Playwright Chromium 系统库在 Render Python 运行时是否齐全 | UI 服务无法启动 → 抓取全部不可用 |
| **High** | 免费档 512 MB 内存 + Chromium 内存占用 | 抓取时 OOM 风险 |
| **High** | 无认证、CORS 全开 | 不适合公网正式推广 |
| **Medium** | `RENTALAI_API_URL` 需手动配置（`sync: false`） | 漏配则 HTTP 路径不通（进程内路径不受影响） |
| **Medium** | 反爬导致空结果 | 业务层风险，有 fallback 提示 |
| **Low** | `area_module.py` 相对路径依赖 cwd | 启动目录正确即可 |
| **Low** | 免费档冷启动慢 | 用户体验，不阻塞功能 |

---

## 6. Recommended Final Deployment Sequence

1. **部署 API 服务**（`rentalai-api`）→ 验证 `GET /health`。
2. **配置 UI 服务环境变量** `RENTALAI_API_URL` = API 公网 URL。
3. **部署 UI 服务**（`rentalai-ui`，含 Playwright build）→ 观察 build 日志。
4. **冒烟测试 A（进程内）**：Agent Parse → Continue → 小量抓取 + 分析。
5. **冒烟测试 B（HTTP）**：关闭 Use local engine → Analyze Property → 确认打到公网 API。
6. **端到端确认**：结果卡片、Top Recommendation、pipeline stats 显示正常。
7. **可选加固**：持久盘、CORS 收紧、认证。
8. **正式上线收尾**（Phase2 Step4）。

---

## 7. Verdict

**Ready for final deployment step.**

所有代码路径（前端 → 后端、前端 → 分析桥、前端 → 抓取）在架构上已打通，环境变量体系完整，部署配置（`render.yaml` / `render.frontend.yaml` / `render.backend.yaml`）与代码入口一致。

唯一的 **未验证项** 是 Playwright Chromium 在目标 PaaS 上的 build 兼容性——这只能通过一次真实部署来确认，不属于代码或配置层面的阻塞。

结论：**可以进入最后的部署执行与端到端验证阶段。**
