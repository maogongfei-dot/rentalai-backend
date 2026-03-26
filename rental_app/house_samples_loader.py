"""
Phase A2：本地样本房源数据加载（realistic / demo），原始 dict 供后续 normalize_house_record(s) 使用。
Phase A3：多来源原始样本（source_samples_*.json）→ load_multi_source_* → 推荐链路可选前置。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_DATA_DIR = Path(__file__).resolve().parent / "data"
_REALISTIC_FILENAME = "realistic_house_samples.json"
_DEMO_FILENAME = "ai_demo_listings.json"
_MULTISOURCE_FILES: tuple[tuple[str, str], ...] = (
    ("source_samples_rightmove.json", "rightmove_style"),
    ("source_samples_zoopla.json", "zoopla_style"),
    ("source_samples_openrent.json", "openrent_style"),
)


def _read_json_list(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return [x for x in raw if isinstance(x, dict)]
    except (OSError, json.JSONDecodeError):
        return []


def load_house_samples(dataset: str = "realistic") -> list[dict[str, Any]]:
    """
    数据加载逻辑：dataset 为 realistic → Phase A2 英国风格样本；demo → 原 ai_demo_listings。
    """
    ds = (dataset or "realistic").strip().lower()
    if ds == "realistic":
        return _read_json_list(_DATA_DIR / _REALISTIC_FILENAME)
    if ds == "demo":
        return _read_json_list(_DATA_DIR / _DEMO_FILENAME)
    return []


def load_realistic_house_samples() -> list[dict[str, Any]]:
    """realistic sample 数据入口（与 load_house_samples('realistic') 等价）。"""
    return load_house_samples("realistic")


def load_multi_source_house_samples_raw() -> list[dict[str, Any]]:
    """
    多来源 loader：合并各 JSON 原始行，行内带 source；供 ai_recommendation_bridge 前置池或测试。
    """
    merged: list[dict[str, Any]] = []
    for filename, default_src in _MULTISOURCE_FILES:
        for row in _read_json_list(_DATA_DIR / filename):
            if not isinstance(row, dict):
                continue
            r = dict(row)
            r.setdefault("source", default_src)
            merged.append(r)
    return merged


def load_multi_source_house_samples() -> list[dict[str, Any]]:
    """
    多来源 loader：clean_and_normalize 后的 canonical 列表（便于单测或 API 调试）。
    """
    from house_source_adapters import clean_and_normalize_house_record

    out: list[dict[str, Any]] = []
    for row in load_multi_source_house_samples_raw():
        src = str(row.get("source") or "unknown")
        out.append(clean_and_normalize_house_record(row, source=src))
    return out
