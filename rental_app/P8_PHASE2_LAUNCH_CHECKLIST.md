# P8 Phase2 Launch Checklist

照着打勾即可。详细说明见 `P8_PHASE2_GO_LIVE_RUNBOOK.md`。

---

## Pre-Launch

- [ ] Git 远程分支已推送，包含 `render.yaml` 和 `rental_app/` 完整代码
- [ ] 本地已试跑 `uvicorn api_server:app` + `curl /health` 成功
- [ ] 本地已试跑 `streamlit run app_web.py`，首页加载正常

## Backend（rentalai-api）

- [ ] Render 创建 Web Service（或 Blueprint），Root Dir = `rental_app`
- [ ] Build Command = `pip install -r requirements.txt`
- [ ] Start Command = `uvicorn api_server:app --host 0.0.0.0 --port $PORT`
- [ ] Health Check Path = `/health`
- [ ] Deploy 成功，服务状态 Live
- [ ] `curl https://<API_URL>/health` 返回 `{"status":"ok",...}`

## Frontend（rentalai-ui）

- [ ] Render 创建 Web Service（或 Blueprint），Root Dir = `rental_app`
- [ ] Build Command = `pip install -r requirements.txt && playwright install chromium`
- [ ] Start Command = `streamlit run app_web.py --server.port $PORT --server.address 0.0.0.0`
- [ ] 环境变量 `RENTALAI_USE_LOCAL` = `1`
- [ ] 环境变量 `RENTALAI_API_URL` = 后端公网 URL（无尾部斜杠）
- [ ] Build 日志确认 `playwright install chromium` 成功
- [ ] Deploy 成功，服务状态 Live
- [ ] 浏览器打开 UI 公网 URL，Streamlit 首页加载正常
- [ ] 侧栏 API base URL 显示公网 API 地址（非 localhost）

## Integration

- [ ] `Use local engine` 开启 → Analyze Property → 返回分析结果
- [ ] `Use local engine` 关闭 → Analyze Property → 返回来自公网 API 的分析结果
- [ ] Batch JSON → Run batch request → 返回结果

## Scraper（Agent 真实抓取）

- [ ] Agent 输入意图 → Parse 成功
- [ ] Continue to Analysis → spinner 启动
- [ ] 等待完成：出现结果卡片 **或** "No listings found"（不崩溃即可）
- [ ] 若 Playwright build 失败：已记录，标记为后续 Docker 化处理

## Final

- [ ] 两个服务 Render Dashboard 状态均为 Live
- [ ] Logs 无 Python traceback / OOM kill
- [ ] 已记录 API 公网 URL：`https://____________________`
- [ ] 已记录 UI 公网 URL：`https://____________________`
- [ ] **MVP Go-Live 完成**
