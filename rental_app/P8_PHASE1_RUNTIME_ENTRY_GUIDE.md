# P8 Phase1 Runtime Entry Guide

本文描述 **RentalAI `rental_app`** 在开发与最小部署场景下的进程入口；与业务功能无关的编排说明。

---

## 1. Frontend Entry

| 项 | 说明 |
|----|------|
| **入口文件** | `app_web.py` |
| **启动命令** | `streamlit run app_web.py`（工作目录：`rental_app`） |
| **默认端口** | `8501`（可用环境变量 `STREAMLIT_SERVER_PORT` 等覆盖，见 Streamlit 官方文档） |
| **依赖说明** | `requirements.txt` 中的 `streamlit`；与 FastAPI 联调时需 `requests` |

**环境变量（应用内读取）**：`RENTALAI_API_URL`、`RENTALAI_USE_LOCAL`（见 `.env.example`）。

---

## 2. Backend Entry

| 项 | 说明 |
|----|------|
| **入口文件** | `api_server.py`（FastAPI 实例名 `app`） |
| **启动命令** | `uvicorn api_server:app --host 0.0.0.0 --port 8000`（本地调试可将 host 改为 `127.0.0.1`） |
| **默认端口** | `8000`（由 uvicorn 命令行指定，非代码内写死） |
| **依赖说明** | `fastapi`、`uvicorn[standard]` |

**说明**：当前仓库 **未** 从环境变量读取 `PORT`/`HOST`；PaaS 部署时一般在启动命令中使用平台提供的 `$PORT`。

---

## 3. Scraper Entry

| 项 | 说明 |
|----|------|
| **库入口** | `data/scraper/playwright_runner.py`（浏览器会话）、`data/scraper/rightmove_scraper.py`、`data/scraper/zoopla_scraper.py`（列表页解析） |
| **编排** | `data/pipeline/rightmove_pipeline.py`、`zoopla_pipeline.py`、`multi_source_pipeline.py`、`analysis_bridge.py` |
| **CLI 调试** | `scripts/run_rightmove_pipeline.py`、`run_zoopla_pipeline.py`、`run_multi_source_pipeline.py`、`run_multi_source_analysis.py`、`run_rightmove_scrape.py`、`run_zoopla_probe.py` 等 |
| **启动命令（示例）** | `python scripts/run_multi_source_pipeline.py --sources rightmove --limit 3` |
| **是否建议独立运行** | **开发/运维**：可用脚本或 cron 单独跑 pipeline。**与 Streamlit 同进程**：用户点击 Agent / 真实多源分析时，抓取在 **Streamlit 进程内** 同步执行，长耗时、占资源。 |
| **与后端关系** | FastAPI **仅** 暴露 `/analyze`、`/analyze-batch` 等分析接口，**不** 暴露抓取 HTTP 路由；抓取结果若落盘，经 `data/storage` 写入 JSON（路径可由 `RENTALAI_LISTINGS_PATH` 覆盖）。 |

---

## 4. Local Run Order

**最小可跑（只看 UI + 本地引擎 + 真实抓取）**

1. `cd rental_app`
2. `pip install -r requirements.txt` && `playwright install chromium`
3. （可选）配置 `.env` 或导出 `RENTALAI_USE_LOCAL=1`
4. `streamlit run app_web.py`

**需要 HTTP API 联调（单条分析或 batch JSON 走网络）**

1. 终端 A：`uvicorn api_server:app --host 127.0.0.1 --port 8000`
2. 终端 B：`export RENTALAI_API_URL=http://127.0.0.1:8000` 且侧栏 **关闭** Use local engine（或按需只关 batch）
3. `streamlit run app_web.py`

**仅验证抓取（无 Streamlit）**

1. `python scripts/run_rightmove_pipeline.py --limit 2 --no-save`（等）

---

## 5. Production Notes

- **第一版蓝图**：仓库根 **`render.yaml`**（Render）定义 **rentalai-api** 与 **rentalai-ui** 两条 Web 服务，详见 **`P8_PHASE1_DEPLOYMENT_PLAN.md`**。
- **双进程**：公网常见形态为 **Streamlit + Uvicorn** 各一进程，前置反向代理；监听地址需用 `0.0.0.0` 而非仅 `127.0.0.1`。
- **Playwright**：目标环境必须能安装并运行 Chromium；只读根文件系统时需配置 `PLAYWRIGHT_BROWSERS_PATH` 等到可写路径。
- **持久化**：多实例部署时，若使用默认 JSON 文件，需 **共享卷** 或 **单一写实例**；见 `RENTALAI_LISTINGS_PATH`。
- **`area_module.py`**：仍使用当前工作目录下的 `area_data.json`；与 `module2_scoring` 使用的 `data/area_data.json` 路径策略不一致，部署时请以 **在 `rental_app` 目录启动** 为准，或后续单独治理该遗留模块。
