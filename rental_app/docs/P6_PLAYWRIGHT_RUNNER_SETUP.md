# P6 Phase2 — Playwright 环境接入与页面探针

## 本阶段已完成

- 在 `requirements.txt` 中声明 **Python `playwright`** 依赖。
- 实现 **`run_playwright_page_probe(config)`**：启动 Chromium、打开 `ScraperRunConfig.search_url`、等待 `domcontentloaded`，读取 **最终 URL、标题、HTML 长度**；失败时结构化返回，不向外抛未捕获异常。
- **`run_rightmove_probe` / `probe_rightmove_search`**：Rightmove 专用入口；未传 URL 时使用默认租房入口页（可换为自有测试链接）。
- **`scripts/run_rightmove_probe.py`**：本地一键打印探针 JSON 结果。
- 可选调试：当 `save_raw_html` / `save_screenshots` 为真时，向 **`data/scraper/samples/debug/`**（或 `output_dir`）写入 HTML / 截图；写入失败不影响探针成功判定。
- **`run_playwright_scrape`** 仍为 Phase3+ 预留，**当前恒返回 `[]`**，不做 listing 解析。

## 安装依赖

在 **`rental_app`** 目录下：

```bash
pip install -r requirements.txt
```

## 安装浏览器运行时（每台机器一次）

Playwright 需要下载 Chromium（与 pip 包分离）：

```bash
playwright install chromium
```

若系统找不到 `playwright` 命令（常见于 Windows 脚本目录未进 PATH），可用：

```bash
python -m playwright install chromium
```

若仅安装包未执行上述命令，探针可能报错（可执行失败信息会出现在返回的 `error` 字段）。

## 运行最小探针

**方式 A（推荐）**：项目根为 `rental_app`：

```bash
cd rental_app
python scripts/run_rightmove_probe.py
```

**方式 B**：在代码中调用：

```python
from data.scraper import run_rightmove_probe, run_playwright_page_probe, ScraperRunConfig

# Rightmove 默认 URL
print(run_rightmove_probe(headless=True))

# 任意 source + URL（与 Phase3 RightmoveScraper 对接同一 ScraperRunConfig）
cfg = ScraperRunConfig(source="rightmove", search_url="https://www.rightmove.co.uk/property-to-rent.html")
print(run_playwright_page_probe(cfg))
```

成功时 JSON / dict 中含：`success`, `source`, `url`, `final_url`, `page_title`, `html_length`；失败时 `success` 为 false 且 `error` 有说明。

## 探针范围说明

- **仅验证页面可访问与基础元数据**，不解析列表卡片、不提取价格/房型/postcode。
- **不修改** schema / normalizer / storage 核心逻辑。

## 下一阶段（P6 Phase3）

- 在 **Rightmove** 上实现首个真实列表抽取（selectors + `list[dict]`），再接入既有 normalizer 链路。

## 轻量自测（不联网）

在 `rental_app` 下：

```bash
python test_playwright_probe.py
```

该脚本校验空 URL、返回字段形状等；**不要求**成功连接 Rightmove。
