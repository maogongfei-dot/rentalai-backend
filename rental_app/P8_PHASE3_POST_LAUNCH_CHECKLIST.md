# P8 Phase3 Post-Launch Checklist

上线后首轮值班检查。照着打勾即可。

---

## Frontend

- [ ] `https://<UI_URL>/` 首页可访问，Streamlit 标题可见
- [ ] 页面无红色错误提示
- [ ] 侧栏 API base URL 显示公网后端地址（非 `127.0.0.1`）
- [ ] `Use local engine` 开启 → Analyze Property → 返回分析结果

## Backend

- [ ] `GET https://<API_URL>/health` 返回 HTTP 200 + `{"status":"ok",...}`
- [ ] `POST /analyze` 用合法 body 返回分析结果
- [ ] Render Logs 无 Python traceback / OOM kill

## Integration

- [ ] `Use local engine` 关闭 → Analyze Property → 返回来自公网 API 的结果
- [ ] 验证 1（进程内）+ 验证 2（HTTP API）均通过 = 整站 MVP 已打通

## Scraper（Agent 真实抓取）

- [ ] 确认 Playwright build 是否成功（查 UI 服务 build 日志）
- [ ] 若成功：Agent Parse → Continue → 出现结果或 "No listings found"（不崩溃）
- [ ] 若失败：已记录，标记为后续 Docker 化处理，**不阻止主站上线**

## Monitoring

- [ ] 已知道前端报错先看哪里：Render Dashboard → rentalai-ui → Logs
- [ ] 已知道后端报错先看哪里：Render Dashboard → rentalai-api → Logs
- [ ] 已知道排查顺序：502→Logs | 超时→冷启动等待 | 500→traceback | OOM→升配

## URLs

- [ ] API 公网 URL：`https://____________________`
- [ ] UI 公网 URL：`https://____________________`

## Verdict

- [ ] **MVP Go-Live 验证通过**
