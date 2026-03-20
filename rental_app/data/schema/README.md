# Listing schema（P3 Phase1）

## 作用

- **`ListingSchema`**（`listing_schema.py`）是 RentalAI **全项目统一的标准房源结构**。
- 后续来自 **API、手工表单、Rightmove、Zoopla** 等的数据，都应先归一到此结构，再视需要转为现有 **`/analyze`** / **`/analyze-batch`** 入参。

## 当前阶段不包含

- 爬虫（scraper）
- 归一化流水线（normalizer）
- 数据库持久化

本目录 **只提供 schema 与轻量辅助**（`to_dict` / `from_dict` / `is_valid_listing_payload` / `LISTING_SCHEMA_FIELDS`），为上述阶段打底。

## 与现有分析接口的关系

- 分析引擎当前仍使用 **`web_bridge.normalize_web_form_inputs`** 所期望的字段名（如 `rent`、`area`、`postcode` 等）。
- 可选使用 **`convert_listing_schema_to_analyze_payload`** 将 `ListingSchema` 映射为该字典格式；**本 Phase 不要求**在 API 路由中强制接入。

## 文件

| 文件 | 说明 |
|------|------|
| `listing_schema.py` | `ListingSchema`、`LISTING_SCHEMA_FIELDS`、校验与转换辅助函数 |
