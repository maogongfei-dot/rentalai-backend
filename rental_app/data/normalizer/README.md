# Listing normalizer（P3 Phase2）

## 职责

- 把 **manual / API / Rightmove / Zoopla / unknown** 等来源的 **原始 `dict`** 统一转成 **`ListingSchema`**。
- **不负责** 网页抓取、HTTP 请求、数据库。

## 入口

| 函数 | 说明 |
|------|------|
| `normalize_listing_payload(data, source=None)` | 单条 → `ListingSchema` |
| `normalize_listing_batch(items, source=None)` | 批量 → `list[ListingSchema]`，单条失败降级为最小 schema |
| `to_analyze_payload(listing, budget=..., target_postcode=...)` | 数据层：`ListingSchema` → 与现有 `/analyze` 兼容的 `dict`（**未接入路由**） |

`source` 优先使用参数；否则读 `data["source"]`；无法识别则为 **`unknown`**。

## 与后续 scraper 的关系

Rightmove / Zoopla 爬虫将来产出的原始 dict，也应 **先经本 normalizer** 再进入业务或存储。

## 与 Phase1 的关系

最终统一通过 **`ListingSchema.from_dict(...)`** 构造；并写入 **`normalized_at`**（UTC ISO）、**`raw_data`**（原始快照）、**`source`**。
