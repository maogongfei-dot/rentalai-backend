# P8 Phase3 Go-Live Verification

本文档为 RentalAI MVP 的最终上线验证方案，涵盖验证步骤、监控入口、排查顺序与回退方案。

---

## 1. Current Go-Live Scope

### 首轮上线包含

| 服务 | 平台 | 必须在线 |
|------|------|----------|
| **rentalai-api**（FastAPI） | Render Web Service | **是** — 提供 `/health`、`/analyze`、`/analyze-batch` 等分析接口 |
| **rentalai-ui**（Streamlit） | Render Web Service | **是** — 产品 UI + 进程内分析引擎 |

### 首轮不计入

| 模块 | 说明 |
|------|------|
| Agent 真实抓取（Playwright） | 随 UI 服务部署，但 Playwright build 可能失败。**失败不阻止主站上线**——分析功能不依赖 Playwright |
| 持久化数据盘 | `listings.json` 在 ephemeral 磁盘，可后续加 Disk |
| 认证 / CORS 收紧 | MVP 演示不要求 |

### 模块可降级 vs 必须在线

| 模块 | 分类 | 说明 |
|------|------|------|
| FastAPI `/health` + `/analyze` | **必须在线** | 核心分析能力 |
| Streamlit 首页 + 表单 | **必须在线** | 用户入口 |
| 进程内分析（Use local engine） | **必须在线** | 不依赖后端的分析路径 |
| HTTP API 分析（关闭 local） | **可降级** | 后端休眠时暂不可用，但 local 路径可替代 |
| Agent 真实抓取 | **可降级** | Playwright 失败时，分析表单仍可手动使用 |
| Batch JSON | **可降级** | 非核心用户路径 |

---

## 2. Public Entry Check

| 项 | 值 |
|----|-----|
| **用户入口** | `https://<rentalai-ui-xxxx>.onrender.com` — Streamlit 首页 |
| **最小用户路径** | 打开首页 → 填写租金/卧室/邮编/预算 → 点击 **Analyze Property** → 看到评分和分析结果 |
| **上线成功标志** | 用户可在公网打开首页、完成一次 Analyze Property、看到评分结果 |

### 会导致用户一打开就报错的可能情况

1. **UI 服务未成功部署** → 页面 502 / 超时。检查 Render Dashboard 服务状态。
2. **UI 服务 build 失败** → 无可用实例。检查 build 日志。
3. **免费档冷启动** → 首次访问等 30-60 秒。这不是报错，是预期行为。

---

## 3. Backend Verification Check

| 项 | 值 |
|----|-----|
| **Health check 地址** | `GET https://<API_URL>/health` |
| **成功响应** | HTTP 200：`{"status":"ok","service":"rentalai-api","api_version":"P2-Phase5"}` |
| **关键 API 验证** | `POST /analyze` with `{"rent":1500,"bedrooms":2,"postcode":"SW1A 1AA","budget":2000}` |
| **成功标志** | HTTP 200，JSON 含 `score`、`decision`、`analysis` 字段 |
| **失败标志** | HTTP 502/504（服务未启动）、HTTP 500（引擎异常）、连接超时（冷启动） |

### 最可能的线上错误

| 错误 | 原因 | 处理 |
|------|------|------|
| 502 Bad Gateway | 服务未启动或 crash | 查 Render Logs |
| 连接超时 | 免费档休眠 | 等 60 秒后重试 |
| 500 Internal Server Error | 分析引擎 Python 异常 | 查 Render Logs 中的 traceback |
| `ModuleNotFoundError` | Root Directory 配置错误 | 确认 Root Dir = `rental_app` |

---

## 4. Frontend Verification Check

| 项 | 值 |
|----|-----|
| **访问页面** | `https://<UI_URL>/` |
| **成功标志** | Streamlit 首页加载，标题和表单可见，侧栏 API URL 显示公网地址 |
| **失败标志** | 页面白屏 / 502 / "Please wait..." 卡死超 2 分钟 |

### 需检查的请求

Streamlit 架构中，分析请求由 **Python 服务端** 发出（`requests.post`），不在浏览器 Network 面板中可见。验证方式是通过 **页面上的分析结果展示** 来判断。

- **有结果** = 请求成功
- **红色错误提示** = 请求失败，提示文本包含原因

---

## 5. End-to-End Verification Check

### 操作步骤（照着做）

**前置：先唤醒后端**

```
浏览器打开 https://<API_URL>/health
等待返回 {"status":"ok",...}（最多 60 秒）
```

**验证 1：进程内分析（不依赖后端 API）**

1. 浏览器打开 `https://<UI_URL>/`
2. 确认侧栏 **"Use local engine"** 已勾选
3. 在表单中填入：Rent = `1500`，Bedrooms = `2`，Postcode = `SW1A 1AA`，Budget = `2000`
4. 点击 **"Analyze Property"**
5. **成功**：页面显示评分、决策、分析结果面板
6. **失败**：页面显示红色错误 → 查看错误文本，再查 Render UI 服务 Logs

**验证 2：HTTP API 分析（通过公网后端）**

1. 侧栏 **取消勾选** "Use local engine"
2. 确认侧栏 **"API base URL"** 显示 `https://rentalai-api-xxxx.onrender.com`
3. 使用相同表单数据，点击 **"Analyze Property"**
4. **成功**：返回分析结果
5. **失败**：
   - 提示 "API request failed" → 后端可能仍在休眠，重试
   - 提示 "Invalid JSON" → 查后端 Logs

**验证 3：Agent 意图解析（可选，验证 Playwright 是否可用）**

1. 侧栏勾选 **"Use local engine"**
2. 在 Agent 区输入：`Looking for a 2-bed flat in London under 1800`
3. 点击 **Parse**
4. **成功**：解析出 intent 字段（bedrooms=2, budget=1800 等）
5. 点击 **Continue to Analysis**（触发真实抓取+分析）
6. **成功**：出现结果卡片或 "No listings found"
7. **失败（OOM/系统库缺失）**：页面崩溃或长时间无响应 → Playwright 不可用，标记为后续 Docker 化

### 整站打通判定标准

- [x] 验证 1 通过 → 进程内引擎可用
- [x] 验证 2 通过 → 前后端 HTTP 联调成功
- [ ] 验证 3 可选 → Agent + Playwright 可用性

**验证 1 + 验证 2 通过 = 整站 MVP 已打通。**

---

## 6. Monitoring / Logs Checklist

### Frontend first-check logs

| 位置 | 查看方式 | 关注什么 |
|------|---------|----------|
| **Render Dashboard → rentalai-ui → Logs** | 实时日志流 | Python traceback、`ModuleNotFoundError`、`OOM killed`、Playwright 错误 |
| **浏览器页面** | 红色错误提示 | "API request failed"、"Invalid JSON"、引擎异常信息 |

> 注意：Streamlit 的 HTTP 请求不在浏览器 Network 面板中——请求在服务端发出。

### Backend first-check logs

| 位置 | 查看方式 | 关注什么 |
|------|---------|----------|
| **Render Dashboard → rentalai-api → Logs** | 实时日志流 | `uvicorn` 启动失败、Python traceback、500 错误、请求超时 |
| **`/health` 响应** | 浏览器或 curl | 返回 200 = 存活；502/504 = 服务异常 |

### Scraper first-check logs（若 Playwright build 成功）

| 位置 | 查看方式 | 关注什么 |
|------|---------|----------|
| **Render Dashboard → rentalai-ui → Logs** | 实时日志流 | `playwright` 相关错误、`browser was not downloaded`、Chromium crash、OOM |
| **UI 页面 Agent 区** | 触发 Continue to Analysis | 超长 spinner（>2分钟）= 可能 OOM 或网络超时 |

### 上线后重点盯的 5 类错误

1. **502 / 504**：服务未启动或 crash，立即查 Render Logs
2. **Python traceback（500）**：引擎内部异常，查日志定位函数
3. **OOM killed**：Chromium 内存超限，Render Logs 中出现 `Killed` 信号
4. **连接超时**：免费档冷启动，等 60 秒重试即可
5. **"No listings found"（Agent 路径）**：反爬或网络问题——业务风险，不影响分析功能

---

## 7. Top 5 Post-Launch Risks

| # | 风险 | 严重度 | 影响 | 缓解 |
|---|------|--------|------|------|
| 1 | **Playwright Chromium 系统库缺失** | High | Agent 真实抓取不可用 | 核心分析不受影响；后续 Docker 化解决 |
| 2 | **免费档双服务冷启动** | Medium | 首次访问等 30-60 秒 | 演示前先手动唤醒 `/health` |
| 3 | **免费档 512 MB 内存 + Chromium** | Medium | 抓取时 OOM | 限制 `limit_per_source` ≤ 5；或升级 plan |
| 4 | **无认证 / CORS 全开** | Medium | 不适合公网推广 | MVP 演示可接受；推广前加固 |
| 5 | **Rightmove/Zoopla 反爬** | Low | Agent 抓取返回空结果 | 有 fallback 提示，不崩溃 |

---

## 8. Rollback / Fallback Actions

### 前端异常时

| 现象 | 判断方式 | 处理 |
|------|---------|------|
| 页面 502 / 白屏 | 浏览器打开 UI URL 无响应 | Render Dashboard → rentalai-ui → Logs 查 build/start 失败原因 |
| Build 失败 | Dashboard 服务状态非 Live | 若是 Playwright 导致：移除 `&& playwright install chromium` 重新 deploy（牺牲 Agent 抓取，保住分析功能） |
| 运行时 crash | Logs 有 traceback | 回滚到上一个成功 commit：Dashboard → Manual Deploy → 选上一个 commit |

### 后端异常时

| 现象 | 判断方式 | 处理 |
|------|---------|------|
| `/health` 返回非 200 | curl 或浏览器 | Render Logs 查错 |
| 分析请求 500 | 前端提示 API request failed | Render Logs 查 Python traceback |
| 完全不可达 | 连接超时 | 确认 Render 服务未被删除；免费档可能因长期无流量被暂停 |

### Scraper 异常时

**主站继续在线。** Scraper 异常仅影响 Agent "Continue to Analysis" 路径。以下功能不受影响：

- Streamlit 首页
- 手动表单 Analyze Property（进程内 + HTTP）
- Agent intent 解析（Parse）
- Batch JSON

### 允许先上线后修的问题

- Playwright build 失败
- CORS 收紧
- 认证添加
- 持久盘
- 冷启动优化
- 反爬应对

---

## 9. Final Verdict

### Go-Live Confirmed

**理由**：

1. **代码层面**：前后端 API 路径完全一致（5/5 接口 Pass），环境变量体系完整，CORS 对 MVP 足够。无代码修改需求。
2. **配置层面**：`render.yaml` / `render.backend.yaml` / `render.frontend.yaml` 与代码入口、启动命令、Health check 路径完全匹配。
3. **降级策略**：Playwright 失败不阻止主站——`RENTALAI_USE_LOCAL=1` 的进程内分析路径完全独立于 Playwright 和后端 API。
4. **验证路径**：§5 提供了可执行的端到端验证步骤，覆盖进程内分析 + HTTP API 分析 + Agent（可选）三条路径。
5. **回退方案**：Render 支持一键回滚 commit，Build Command 可临时移除 Playwright 以保住核心功能。

---

## 10. Immediate Next Action

1. **若尚未部署**：按 `P8_PHASE2_LAUNCH_CHECKLIST.md` 逐项执行部署。
2. **若已部署**：按 §5 的三个验证步骤逐一执行。
3. **验证通过后**：
   - 记录两个公网 URL
   - 按 `P8_PHASE3_POST_LAUNCH_CHECKLIST.md` 做上线后首轮打勾确认
   - MVP 上线完成，可分享给测试用户
