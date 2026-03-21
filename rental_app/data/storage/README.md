# Listing storage（P3 Phase3）

## 职责

- 将 **已标准化的 `ListingSchema`** 写入本地 **JSON** 文件，并读取为 **`list[ListingSchema]`**。
- **不包含**：爬虫、SQLite/PostgreSQL/ORM、与 `/analyze` 路由的强制绑定。

## 默认路径

- **`rental_app/data/listings.json`**（由 `DEFAULT_LISTINGS_PATH` 集中定义）
- 若设置环境变量 **`RENTALAI_LISTINGS_PATH`**（绝对或用户目录路径），则覆盖默认文件位置，便于挂载卷部署。
- 父目录不存在时会自动创建；文件不存在时读取为 **空列表**。

## 入口函数

| 函数 | 说明 |
|------|------|
| `save_listing(listing, file_path=None)` | 单条；支持 `ListingSchema` 或 `dict`（先 `from_dict`） |
| `save_listings(listings, file_path=None)` | 批量；单条异常计入 `skipped` |
| `load_listings(file_path=None)` | 全部；坏行跳过 |
| `load_listings_by_source(source, file_path=None)` | 按 `source` 过滤 |
| `get_listing_by_id(listing_id, source=None, file_path=None)` | 按 id；可选限定 `source` |
| `export_listings_as_dicts(file_path=None)` | `list[dict]`，便于调试 |

## 去重 / 更新规则

1. 若存在 **`source` + `listing_id`**（`listing_id` 非空）→ 以此作为唯一键，**存在则覆盖**。
2. 否则若存在 **`source` + `source_url`**（`source_url` 非空）→ 同上。
3. 若两者都不能构成键 → **总是追加**（不合并）。

## 数据流建议

外部数据 → **Normalizer** → `ListingSchema` → **本 storage** → 后续 API / 分析再按需使用 `to_analyze_payload` 等（本阶段不接入主流程）。
