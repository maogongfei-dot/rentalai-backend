# P8 Phase2 Scraper Deploy Prep

本文档对应 **Phase2 Step3**，整理抓取模块（Scraper）的运行要求与部署方案。

---

## 1. Scraper Entry

| 项 | 说明 |
|----|------|
| **核心入口** | `data/scraper/playwright_runner.py` — Chromium 启动、页面探针、通用 `run_playwright_scrape()` 分发 |
| **平台抓取器** | `data/scraper/rightmove_scraper.py`、`data/scraper/zoopla_scraper.py` |
| **编排层** | `data/pipeline/rightmove_pipeline.py`、`zoopla_pipeline.py`、`multi_source_pipeline.py` |
| **分析桥** | `data/pipeline/analysis_bridge.py`（`run_multi_source_analysis`） |
| **调试脚本** | `scripts/run_rightmove_pipeline.py`、`run_zoopla_pipeline.py`、`run_multi_source_pipeline.py`、`run_multi_source_analysis.py` 等 |
| **启动方式** | **无独立常驻进程**。抓取在 **Streamlit 进程内同步执行**，由用户点击 Agent → "Continue to Analysis" 或 "Run real multi-source analysis" 按钮触发 |
| **与后端关系** | FastAPI（`api_server.py`）**不**调用抓取模块；分析接口 `/analyze` `/analyze-batch` 不依赖 Playwright。抓取结果落盘后，后端可通过 `listing_storage` 读取（如有），但当前无自动联动 |

---

## 2. Runtime Requirements

### Python 依赖

| 包 | 版本 | 用途 |
|----|------|------|
| `playwright` | ≥ 1.40.0 | Chromium 自动化驱动 |
| `streamlit` | ≥ 1.28.0 | 宿主进程（Scraper 嵌于其中） |
| `requests` | ≥ 2.31.0 | 非 Scraper 直接依赖，但 `requirements.txt` 含 |

以上均已收录于 `rental_app/requirements.txt`。

### 浏览器依赖

- **Chromium**：需在 build 阶段执行 `playwright install chromium`。
- 该命令将下载约 **~130 MB** 浏览器二进制到默认缓存目录（或 `PLAYWRIGHT_BROWSERS_PATH` 指定路径）。

### 系统环境要求

| 要求 | 说明 |
|------|------|
| **系统库** | Playwright Chromium 在 Linux 上依赖 `libnss3`、`libatk-bridge2.0-0`、`libgbm1` 等。Render Python 运行时预装部分库，但不保证全部满足；若缺失需改用 Docker 运行时 |
| **出站网络** | 必须能 HTTPS 访问 `www.rightmove.co.uk`、`www.zoopla.co.uk` |
| **CPU / 内存** | 无头 Chromium 单实例约 **200–400 MB RSS**；Render 免费档 512 MB 紧张 |
| **磁盘** | build 产物 + Chromium ≈ 200 MB；运行时写 HTML/截图需可写文件系统（`/tmp` 可用） |

### 文件系统要求

- `listings.json` 持久化需要可写路径。默认 `data/listings.json`（相对于 `rental_app/`）在 ephemeral 磁盘上，实例重建丢失。
- 建议生产配置 `RENTALAI_LISTINGS_PATH` 指向持久盘。

---

## 3. Deployment Recommendation

**当前最合适方案：与 Streamlit 同服务、同进程（不拆分）。**

### 理由

1. 抓取代码通过 `real_analysis_service.py` → `analysis_bridge.py` → `multi_source_pipeline` → `playwright_runner` 在 Streamlit 进程内同步调用。拆成独立 Worker 需引入消息队列（Redis/RabbitMQ）和异步轮询，**远超最小可上线范围**。
2. `render.yaml` 的 `rentalai-ui` 服务 buildCommand 已包含 `playwright install chromium`，无需额外部署单元。
3. FastAPI 服务 **无** Playwright 依赖，保持轻量；抓取仅在 UI 服务中运行。

### 未来演进（非本阶段）

- 若抓取耗时导致 Streamlit 超时或 OOM，可拆为 **Render Background Worker** + Redis 队列。
- 若需定时抓取，可加 cron job 调用 `scripts/run_multi_source_pipeline.py`。

---

## 4. Required Environment Variables

Scraper 不单独读取环境变量，但以下变量影响其运行行为：

| 变量 | 来源 | 用途 |
|------|------|------|
| `PLAYWRIGHT_BROWSERS_PATH` | Playwright 官方 | 自定义 Chromium 缓存目录（只读根文件系统时必配） |
| `RENTALAI_LISTINGS_PATH` | `data/storage/listing_storage.py` | 抓取结果持久化路径（可选） |
| `RENTALAI_USE_LOCAL` | `app_web.py` | `1` 时 Agent 走进程内抓取+分析，**不** 走 HTTP |

> `PORT` 由平台注入给 Streamlit，与 Scraper 无直接关系。

---

## 5. Blocking Issues Before Scraper Go-Live

| 优先级 | 问题 | 影响 | 缓解 |
|--------|------|------|------|
| **High** | Playwright Chromium 在 Render Python 运行时可能缺系统库 | build 失败 → UI 服务无法启动 | 首次部署后观察 build 日志；失败则改 Docker 运行时（`mcr.microsoft.com/playwright/python` 镜像） |
| **High** | 免费档 512 MB 内存，Chromium 占 200–400 MB | OOM kill → 抓取中断 | 限制 `limit_per_source` ≤ 5；或升级 plan |
| **Medium** | Rightmove / Zoopla 反爬（Cloudflare、Captcha、IP 封禁） | 抓取返回空结果或报错 | 业务风险，不阻碍部署本身；向用户显示 fallback 消息 |
| **Medium** | 同步抓取阻塞 Streamlit 进程 | 其他用户操作需等待 | 当前演示可接受；生产需 Worker |
| **Low** | 无抓取频率限制 | 理论上用户可密集触发 | 非 MVP 范围 |

---

## 6. Minimal Verification Plan

### build 阶段

1. Render build 日志出现 `playwright install chromium` 成功（`Chromium ... downloaded`）。
2. build 完成、服务状态为 `Live`。

### 运行时验证

1. 打开 Streamlit 公网 URL，进入 Agent 区。
2. 输入合法意图，如 `Looking for a 2-bed flat in London under 1800`。
3. 点击 **Parse** → 确认 intent 解析成功。
4. 点击 **Continue to Analysis** → 观察 spinner 启动。
5. 等待完成（可能 30–90 秒）：
   - **成功**：结果区出现房源卡片、Top Recommendation、pipeline stats。
   - **失败（反爬/网络）**：结果区提示 "No listings found"，**但不崩溃**。
   - **失败（OOM/系统库缺失）**：服务日志报 crash → 需切 Docker 或升配。

### 本地快速验证（不经 Streamlit）

```bash
cd rental_app
python scripts/run_multi_source_analysis.py --sources rightmove --limit 2 --no-save --headless
```

---

## 7. Next Step

1. **首次部署 UI 服务**（含 Playwright build）并观察 build 日志。
2. 若 build 成功 → 按 §6 运行时验证走通 Agent 抓取+分析路径。
3. 若 build 失败 → 进入 **P8 Phase3：Docker 化 UI 服务**（基于 `mcr.microsoft.com/playwright/python` 镜像）。
4. 端到端验证通过后 → 进入 **Phase2 Step4：正式上线收尾**（CORS 收紧、持久盘、监控）。
