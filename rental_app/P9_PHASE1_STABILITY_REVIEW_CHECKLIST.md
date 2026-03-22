# P9 Phase1 Stability Review Checklist

上线后稳定性巡检。定期（如每日或每次演示前）照着打勾。

---

## Frontend

- [ ] `https://<UI_URL>/` 首页可访问，Streamlit 标题可见
- [ ] 页面无红色错误提示 / 无白屏
- [ ] 侧栏 API base URL 显示公网后端地址（非 `127.0.0.1`）
- [ ] `Use local engine` 开启 → Analyze Property → 返回分析结果
- [ ] Render Dashboard → rentalai-ui 状态为 Live

## Backend

- [ ] `GET https://<API_URL>/health` 返回 HTTP 200 + `{"status":"ok",...}`
- [ ] `POST /analyze` 用合法 body 返回分析结果（非 500）
- [ ] Render Dashboard → rentalai-api → Logs 无持续性 traceback / OOM
- [ ] 服务状态为 Live

## Integration

- [ ] `Use local engine` 关闭 → Analyze Property → 返回来自公网 API 的结果
- [ ] 最小用户路径可走通（填表单 → 分析 → 看结果）
- [ ] 环境变量 `RENTALAI_API_URL` 指向正确的后端公网地址

## Scraper

- [ ] 已确认 Playwright build 成功与否（查 UI 服务 build 日志）
- [ ] 若在线：Agent Parse → Continue → 出现结果或 "No listings found"（不崩溃）
- [ ] 若不在线：主站分析功能正常，Agent 抓取路径已标记降级

## Monitoring

- [ ] 前端报错先看：Render Dashboard → rentalai-ui → Logs
- [ ] 后端报错先看：Render Dashboard → rentalai-api → Logs + `curl /health`
- [ ] 问题分级方式已明确（P0 立即 / P1 当天 / P2 本周 / P3 记录）

## Verdict

- [ ] 当前系统进入稳定观察阶段
