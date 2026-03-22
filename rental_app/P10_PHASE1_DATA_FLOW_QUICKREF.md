# P10 Phase1 Data Flow Quick Reference

---

## Task Flow

queued -> running -> success/failed -> DB

---

## Analysis Flow

input -> analysis -> DB -> reuse（if cache hit）

---

## Property Flow

scraper -> extract -> DB

---

## Notes

- 当前为最小数据接入版本。
- 保持现有 task API 与 JSON 路径兼容，SQLite 作为结构化数据层补充。
