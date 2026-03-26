"""
Phase A5：统一候选房源加载（canonical），供推荐引擎使用。
"""

from __future__ import annotations

from typing import Any

from house_samples_loader import load_house_samples, load_multi_source_house_samples
from house_source_adapters import clean_and_normalize_house_records


def load_candidate_houses(
    dataset: str = "realistic",
    imported_records: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """
    按数据来源返回已 clean + normalize 的 canonical 记录列表。
    - demo / realistic：从 JSON 加载后逐条 clean_and_normalize（行内 source 优先）
    - multi_source：与 loader 一致，已为 canonical
    - imported：使用调用方传入的原始行（如 A4 导入前格式）
    """
    ds = (dataset or "realistic").strip().lower()

    if ds == "imported":
        if not imported_records:
            return []
        return clean_and_normalize_house_records(imported_records, source=None)

    if ds == "multi_source":
        return load_multi_source_house_samples()

    if ds == "demo":
        raw = load_house_samples("demo")
        return clean_and_normalize_house_records(raw, source=None)

    if ds == "realistic":
        raw = load_house_samples("realistic")
        return clean_and_normalize_house_records(raw, source=None)

    return []
