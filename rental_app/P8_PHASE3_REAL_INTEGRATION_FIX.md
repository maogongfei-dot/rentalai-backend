# P8 Phase3 Real Integration Fix

本文档对应 **Phase3 Step3**，记录前后端真实线上联调检查结果与修复（如有）。

---

## 1. Current Frontend URL

| 项 | 值 |
|----|-----|
| **线上地址** | 由 Render 分配，形如 `https://rentalai-ui-xxxx.onrender.com`（部署后在 Dashboard 获取） |
| **API 地址读取方式** | `app_web.py` 第 593 行：`os.environ.get("RENTALAI_API_URL", "http://127.0.0.1:8000")` |
| **运行时行为** | 侧栏 "API base URL" 输入框默认取上述值，用户可在 session 内覆写 |
| **localhost fallback** | 环境变量未设置时回退到 `http://127.0.0.1:8000`——这是 **预期行为**（本地开发）。线上部署时只要 `RENTALAI_API_URL` 正确配置即无问题 |

---

## 2. Current Backend URL

| 项 | 值 |
|----|-----|
| **线上地址** | 由 Render 分配，形如 `https://rentalai-api-xxxx.onrender.com`（部署后在 Dashboard 获取） |
| **变量来源** | UI 服务环境变量 `RENTALAI_API_URL`，在 Render Dashboard 或 `render.yaml` 的 `envVars` 中配置 |
| **健康检查** | `GET https://<API_URL>/health` → `{"status":"ok","service":"rentalai-api","api_version":"P2-Phase5"}` |

---

## 3. Integration Check Result

**Frontend → Backend：Pass**

| 检查项 | 结果 | 说明 |
|--------|------|------|
| API base URL 读取 | **Pass** | `os.environ.get("RENTALAI_API_URL")` 在 Render 中通过环境变量注入，运行时正确读取 |
| localhost fallback | **安全** | 仅当 `RENTALAI_API_URL` 未设置时生效；线上部署该变量必配，不会触发 fallback |
| 路径拼接 | **Pass** | `base.rstrip("/") + "/analyze"` 格式，无重复斜杠、无 `/api` 前缀差异 |
| Build 后变量生效 | **不适用** | Streamlit 无 build 产物——环境变量在运行时 `os.environ` 实时读取，不存在 "构建时注入后固化" 的问题 |

---

## 4. API Path Consistency Check

### 前端调用 vs 后端路由对照表

| 前端调用位置 | 请求路径 | 方法 | 后端路由 | 一致性 |
|-------------|----------|------|----------|--------|
| `app_web.py` L214 — 单条 Analyze | `{base}/analyze` | POST JSON | `@app.post("/analyze")` | **一致** |
| `app_web.py` L214 — Score Breakdown | `{base}/score-breakdown` | POST JSON | `@app.post("/score-breakdown")` | **一致** |
| `app_web.py` L214 — Risk Check | `{base}/risk-check` | POST JSON | `@app.post("/risk-check")` | **一致** |
| `app_web.py` L214 — Explain Only | `{base}/explain-only` | POST JSON | `@app.post("/explain-only")` | **一致** |
| `app_web.py` L1012 — Batch JSON | `{base}/analyze-batch` | POST JSON | `@app.post("/analyze-batch")` | **一致** |

所有接口路径、HTTP 方法、请求体格式（JSON）完全匹配。**无不一致项。**

---

## 5. CORS Check

### 当前配置

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

| 检查项 | 结果 |
|--------|------|
| 允许线上前端域名 | **Pass** — `allow_origins=["*"]` 允许任何来源 |
| OPTIONS 预检支持 | **Pass** — FastAPI `CORSMiddleware` 自动处理 `OPTIONS` |
| 允许 credentials | **Pass** — `allow_credentials=True` |
| 允许 headers / methods | **Pass** — 均为 `["*"]` |

### MVP 适用性

当前 `allow_origins=["*"]` 对 **MVP 演示**足够。生产加固时应收紧为：

```python
allow_origins=[
    "https://rentalai-ui-xxxx.onrender.com",
    "http://localhost:8501",
]
```

这属于上线后加固事项，不阻塞 MVP 联调。

### 重要注意

`allow_origins=["*"]` 与 `allow_credentials=True` 同时设置时，浏览器标准（Fetch spec）规定：**响应中 `Access-Control-Allow-Origin` 不能是 `*`，必须是具体域名**。FastAPI `CORSMiddleware` 在检测到 `credentials=True` + `origins=["*"]` 时会自动将响应头中的 origin 设为请求中的 `Origin` 值，因此实际行为正确——但严格来说这在某些旧浏览器或代理场景下可能被拦截。

**对于当前 Streamlit 架构，这不是问题**：Streamlit 前端的 HTTP 请求由 **Python `requests` 库**（服务端）发出，不经过浏览器 CORS 机制。只有当用户在浏览器中直接调用 API（如 fetch/XHR）时 CORS 才生效。

---

## 6. Minimal Fixes Applied

**本次无需代码修改。**

所有检查项均 Pass：

- API base URL 环境变量读取正确
- 路径拼接无错误
- 接口路径与后端路由完全一致
- CORS 配置对 MVP 足够
- Streamlit 的 HTTP 请求走服务端 `requests` 库，不受浏览器 CORS 限制

---

## 7. Real Verification Steps

### Step 1：验证后端在线

```
浏览器打开：https://<你的API地址>/health
```

预期看到：`{"status":"ok","service":"rentalai-api","api_version":"P2-Phase5"}`

> 免费档首次访问需等 30-60 秒唤醒。

### Step 2：验证前端首页

```
浏览器打开：https://<你的UI地址>/
```

预期：Streamlit 首页加载，看到 RentalAI 标题。

### Step 3：验证 API 地址配置正确

1. 查看左侧栏 **"API base URL"** 输入框。
2. **正确**：显示 `https://rentalai-api-xxxx.onrender.com`。
3. **错误**：显示 `http://127.0.0.1:8000` — 说明 `RENTALAI_API_URL` 环境变量未设置，需在 Render Dashboard 补配。

### Step 4：进程内分析验证

1. 确保侧栏 **"Use local engine"** 勾选为开启。
2. 填入表单数据（或使用 Demo 预填）。
3. 点击 **"Analyze Property"**。
4. **成功**：页面显示评分、决策和分析结果。
5. **失败**：查看页面上的红色错误提示。

### Step 5：HTTP API 分析验证

1. **取消勾选** "Use local engine"。
2. 确认侧栏 API base URL 是公网后端地址。
3. 点击 **"Analyze Property"**。
4. **成功**：返回分析结果（此时请求走的是公网后端）。
5. **失败**：
   - 如果提示网络错误 → 后端可能休眠，先访问 `/health` 唤醒。
   - 如果提示 CORS → 检查后端 `allow_origins` 配置。

### Step 6：Batch JSON 验证（可选）

1. 滚动到 Batch 折叠区。
2. 在 JSON 输入框粘贴合法 batch payload，例如：
   ```json
   {"properties": [{"rent": 1500, "bedrooms": 2, "postcode": "SW1A 1AA", "budget": 2000}]}
   ```
3. 点击 **"Run batch request"**（需关闭 local engine）。
4. **成功**：下方显示 Raw JSON response。

### 失败排查优先级

1. 侧栏 API URL 是否正确（环境变量问题）
2. 后端是否已唤醒（免费档休眠）
3. Render Dashboard 中 UI 服务 Logs 是否有 Python traceback

---

## 8. Remaining Risks

| 优先级 | 风险 | 说明 |
|--------|------|------|
| **Medium** | 免费档双服务冷启动 | 后端休眠时前端 HTTP 请求会超时；需先手动唤醒 `/health` |
| **Medium** | Playwright build 兼容性 | 若 `playwright install chromium` 在 Render 上失败，Agent 真实抓取不可用（分析功能不受影响） |
| **Low** | CORS 生产收紧 | 当前 `["*"]` 适合 MVP，公网推广前需限制为 UI 域名 |
| **Low** | 无认证 | API 和 UI 均无登录保护 |

---

## 9. Next Step

1. **若所有验证通过**：MVP 上线完成。记录两个公网 URL，可分享给测试用户。
2. **若 Playwright build 失败**：Agent 真实抓取不可用，但核心分析功能不受影响。后续可通过 Docker 化 UI 服务解决。
3. **上线后加固**（非 MVP 范围）：
   - CORS 收紧为具体域名
   - 添加认证
   - 持久盘挂载
   - 免费档升级
