# P10 Phase2 Features Quick Reference

---

## History

- `GET /records/tasks` — 最近任务（需 `Authorization: Bearer`）；按 `updated_at` 降序。
- `GET /records/analysis` — 最近分析记录；按 `id` 降序。

---

## Favorites

- `POST /favorites` — body：`listing_url` 和/或 `property_id`，可选 `title`、`price`、`postcode`。
- `GET /favorites` — 当前用户收藏列表。
- `DELETE /favorites/{id}` — 删除指定收藏。

---

## Compare

- `POST /compare` — body：`{ "properties": [ {...}, {...}, ... ] }`（2–5 条，与 analyze-batch 行结构兼容）。

---

## Notes

- 当前为最小产品功能版（MVP）；需登录 + 后端 API。
- 后续可接独立页面、JWT、与房源库联动。
