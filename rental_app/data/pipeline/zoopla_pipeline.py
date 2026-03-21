# P6 Phase5：Zoopla 闭环占位 — **不执行真实抓取**（下一阶段镜像 rightmove_pipeline）
from __future__ import annotations

from typing import Any

# 未来实现时的目标链路（与 Phase4 Rightmove 一致）：
#
#   ZooplaScraper.scrape(query, limit)
#       -> list[raw dict]  # 字段策略见 data.scraper.zoopla_scraper 模块文档
#       -> 每条注入 scraped_at（可选，由 pipeline 完成）
#       -> normalize_listing_batch(stamped, source="zoopla")
#       -> save_listings(normalized, file_path=...)
#
# normalizer 已存在 _normalize_zoopla_payload；storage 与 Rightmove 共用 save_listings。


def run_zoopla_pipeline(
    *,
    query: dict[str, Any] | None = None,
    limit: int = 20,
    persist: bool = True,
    storage_path: str | None = None,
    save_raw_sample: bool = False,
    save_normalized_sample: bool = False,
) -> dict[str, Any]:
    """
    Zoopla 版「抓取 → 标准化 → 存储」闭环入口（签名拟与 `run_rightmove_pipeline` 对齐）。

    **P6 Phase5**：仅占位，不调用 Playwright、不写样本、不写 storage。
    """
    _ = query, limit, persist, storage_path, save_raw_sample, save_normalized_sample
    return {
        "success": False,
        "error": (
            "P6 Phase5 placeholder: Zoopla pipeline not implemented; "
            "next phase will mirror run_rightmove_pipeline with source=zoopla."
        ),
        "raw_count": 0,
        "normalized_count": 0,
        "normalization_skipped": 0,
        "saved": 0,
        "updated": 0,
        "skipped": 0,
        "sample_normalized": None,
    }


def scrape_and_normalize_zoopla(**kwargs: Any) -> dict[str, Any]:
    """`run_zoopla_pipeline` 的别名（占位）。"""
    return run_zoopla_pipeline(**kwargs)
