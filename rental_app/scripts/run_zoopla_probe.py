# P6 Phase5：Zoopla 探针占位 — **不访问真实 Zoopla 列表页**
# 下一阶段可用：ScraperRunConfig(source="zoopla", search_url=...) +
#   data.scraper.playwright_runner.run_playwright_page_probe（仅连通性，非 listing 解析）
#
# 在 rental_app 下执行本脚本将打印说明并以非零退出码结束，避免误以为已支持 Zoopla 抓取。
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass
    msg = (
        "P6 Phase5: Zoopla probe 占位 — 未实现真实页面打开与解析。\n"
        "下一阶段：在 zoopla_scraper / playwright_runner 中按 Rightmove 模式接入。\n"
        "临时验证浏览器可用请仍使用: python scripts/run_rightmove_probe.py\n"
    )
    print(msg)
    sys.exit(2)


if __name__ == "__main__":
    main()
