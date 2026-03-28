# RentalAI — 部署后验收清单（P10-5）

适用于：**Render（或同类）后端** + **Vercel 静态前端**分域部署；本地同源 `python run.py` 亦可逐项对照。

## 1. 后端

- [ ] **`GET {API}/health`** 返回 HTTP 200，JSON 含 `success`、`service`、`status`（见 `api_server.py`）。
- [ ] **`ALLOWED_ORIGINS`** 已配置为前端站点 origin（逗号分隔），浏览器控制台无 CORS 报错。

## 2. 前端

- [ ] **首页**（Vercel 根路径 `/`）可打开，静态资源 200。
- [ ] **`/ai-result`** 路由可访问（依赖 `vercel.json` rewrite，刷新不 404）。

## 3. 端到端（自然语言查询）

在首页输入含 **英国地区/邮编** 的英文需求，例如：`2 bed flat in Milton Keynes under 1500 pcm`，点击 **开始分析**。

- [ ] 请求成功进入结果页（非白屏）。
- [ ] **Query Summary** 有内容（原始输入、location 等）。
- [ ] **Market Summary** 有指标或合理占位（无房源时可能为 0）。
- [ ] **Top Deals** 有列表或空状态提示（非白屏）。
- [ ] **Recommendation Report** 有文案或列表占位。

## 4. 异常与空结果

- [ ] 后端关闭或网络失败时，首页显示 **错误文案**（`#ai-err`），可 **重试**。
- [ ] 无地理信息时，结果页有 **请补充位置** 类提示（`housing-missing-location`）。
- [ ] 无足够房源时，有 **空状态** 卡片与返回首页链接（`housing-empty-hint`）。

## 5. 自动化冒烟（可选）

在 `rental_app` 目录：

```bash
set RENTALAI_API_BASE=https://你的后端.onrender.com
python scripts/smoke_test.py
```

详见仓库 `rental_app/README.md` 部署章节。
