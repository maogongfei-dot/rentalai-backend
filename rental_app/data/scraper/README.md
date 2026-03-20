# Scraper（P3 Phase4）

## 职责

- 提供 **外部房源来源** 的统一结构：`BaseListingScraper` + 按 `source` 分发的 **`scrape_listings`**。
- **当前阶段**：仅 **骨架与 mock**，**不做** 真实网页抓取，**不使用** requests / Selenium / Playwright。
- 输出默认为 **`list[dict]`**（原始扁平结构）；需要标准模型时由调用方设 **`normalized=True`**，内部交给 **Phase2 normalizer** → `list[ListingSchema]`。
- **不负责**：storage 持久化、HTTP API 路由、`/analyze` 主流程。

## 支持的 source

| source | 说明 |
|--------|------|
| `rightmove` | 占位，当前 `scrape` 返回 `[]` |
| `zoopla` | 占位，当前 `scrape` 返回 `[]` |
| `manual_mock` | 调试用，返回 2～3 条 mock dict |
| `unknown` | 空列表占位 |

未注册的字符串：**返回空列表**（不抛错）。

## 扩展示意

后续真实 Rightmove / Zoopla 抓取：在对应 `*_scraper.py` 中实现 `scrape()`，保持返回 **`list[dict]`** 即可；无需改统一入口签名。
