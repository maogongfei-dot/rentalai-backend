# P6 Phase1: scraper 侧轻量类型别名（供配置与未来 Playwright 层使用）
from __future__ import annotations

from typing import Any, Literal

# 平台接入顺序（与文档一致）：1) rightmove  2) zoopla；manual_mock 保留开发用
ScraperSourceLiteral = Literal["rightmove", "zoopla", "manual_mock", "unknown"]

# 未来 search job 可扩展的 query 键（Phase2+ 再实填）
ScraperQueryDict = dict[str, Any]
