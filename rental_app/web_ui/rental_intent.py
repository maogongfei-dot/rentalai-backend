# P5 Phase1–4: 自然语言找房 → 结构化目标（类型定义；解析见 rental_intent_parser；Phase4 表单/batch 近似 intent）
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

    @classmethod
    def from_normalized_analyze_form(cls, n: dict[str, Any] | None) -> AgentRentalRequest:
        """P5 Phase4：单条 analyze 规范化表单 → 近似 intent（解释/缺失检测）。"""
        if not isinstance(n, dict):
            return cls()

        def _f(key: str) -> float | None:
            v = n.get(key)
            if v is None:
                return None
            try:
                return float(v)
            except (TypeError, ValueError):
                return None

        def _i(key: str) -> int | None:
            v = n.get(key)
            if v is None:
                return None
            try:
                return int(float(v))
            except (TypeError, ValueError):
                return None

        ar = str(n.get("area") or "").strip() or None
        pc = str(n.get("postcode") or "").strip() or None
        tp = str(n.get("target_postcode") or "").strip() or None
        return cls(
            raw_query="",
            max_rent=_f("rent"),
            target_postcode=tp or pc,
            preferred_area=ar,
            bedrooms=_i("bedrooms"),
            property_type=None,
            bills_included=bool(n.get("bills_included"))
            if isinstance(n.get("bills_included"), bool)
            else None,
            furnished=None,
            max_commute_minutes=_i("commute_minutes"),
            source_preference=None,
            notes=None,
        )

    @classmethod
    def from_batch_first_property(cls, body: dict[str, Any] | None) -> AgentRentalRequest:
        """P5 Phase4：batch 请求 JSON 的第一条 property → 近似 intent。"""
        if not isinstance(body, dict):
            return cls()
        props = body.get("properties")
        if not isinstance(props, list) or not props:
            return cls()
        p0 = props[0] if isinstance(props[0], dict) else {}
        n: dict[str, Any] = dict(p0)
        return cls(
            raw_query="",
            max_rent=_to_float(n.get("rent")),
            target_postcode=(str(n.get("target_postcode") or "").strip() or None),
            preferred_area=(str(n.get("area") or "").strip() or None),
            bedrooms=_to_int(n.get("bedrooms")),
            property_type=None,
            bills_included=n.get("bills_included")
            if isinstance(n.get("bills_included"), bool)
            else None,
            furnished=None,
            max_commute_minutes=_to_int(n.get("commute_minutes")),
            source_preference=None,
            notes=None,
        )


def _to_float(v: Any) -> float | None:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _to_int(v: Any) -> int | None:
    if v is None:
        return None
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return None
