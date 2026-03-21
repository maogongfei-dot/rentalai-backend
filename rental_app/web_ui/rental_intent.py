# P5 Phase1–2: 自然语言找房 → 结构化目标（类型定义；解析见 rental_intent_parser）
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class AgentRentalRequest:
    """
    P5 解析目标结构；字段命名对齐现有 analyze 表单习惯（rent/budget/commute/bedrooms 等）。
    """

    raw_query: str = ""
    max_rent: float | None = None
    target_postcode: str | None = None
    preferred_area: str | None = None
    bedrooms: int | None = None
    property_type: str | None = None
    bills_included: bool | None = None
    furnished: bool | None = None
    max_commute_minutes: int | None = None
    source_preference: str | None = None
    notes: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any] | None) -> AgentRentalRequest:
        if not isinstance(d, dict):
            return cls()
        kw: dict[str, Any] = {}
        for f in (
            "raw_query",
            "max_rent",
            "target_postcode",
            "preferred_area",
            "bedrooms",
            "property_type",
            "bills_included",
            "furnished",
            "max_commute_minutes",
            "source_preference",
            "notes",
        ):
            if f in d:
                kw[f] = d[f]
        return cls(**kw)
