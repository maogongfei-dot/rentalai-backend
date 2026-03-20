# P3 Phase1: 全项目统一标准房源结构（无 scraper / DB / normalizer）
from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from typing import Any, Optional


@dataclass
class ListingSchema:
    """
    标准房源模型：外部来源（Rightmove / Zoopla / manual / API）后续均应先映射到此结构，
    再可选地通过 convert_listing_schema_to_analyze_payload 转为当前 /analyze 入参。
    """

    # --- A. identity ---
    listing_id: Optional[str] = None
    source: Optional[str] = None  # rightmove / zoopla / manual / api / unknown
    source_url: Optional[str] = None
    title: Optional[str] = None

    # --- B. location ---
    address: Optional[str] = None
    postcode: Optional[str] = None
    area_name: Optional[str] = None
    city: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None

    # --- C. pricing ---
    rent_pcm: Optional[float] = None
    deposit: Optional[float] = None
    bills_included: Optional[bool] = None
    council_tax_included: Optional[bool] = None
    other_fees: Optional[list[str]] = None

    # --- D. property ---
    property_type: Optional[str] = None  # flat / house / studio / room / unknown
    bedrooms: Optional[float] = None
    bathrooms: Optional[float] = None
    furnished: Optional[bool] = None
    available_from: Optional[str] = None
    min_tenancy_months: Optional[int] = None
    max_tenancy_months: Optional[int] = None

    # --- E. analysis / compatibility（与 web_bridge / API 对齐）---
    distance_miles: Optional[float] = None
    commute_minutes: Optional[int] = None
    target_postcode_distance_miles: Optional[float] = None

    # --- F. metadata ---
    summary: Optional[str] = None
    scraped_at: Optional[str] = None
    normalized_at: Optional[str] = None
    raw_data: Optional[dict[str, Any]] = None

    def to_dict(self) -> dict[str, Any]:
        """JSON/API 友好 dict；无自定义类型，仅基本类型 + dict / list。"""
        d = asdict(self)
        # 显式保证 other_fees / raw_data 为 list / dict 或 None
        if d.get("other_fees") is None:
            d["other_fees"] = None
        if d.get("raw_data") is None:
            d["raw_data"] = None
        return d

    @classmethod
    def from_dict(cls, data: dict) -> ListingSchema:
        """从普通 dict 构造；未知字段忽略；缺省用 dataclass 默认值。"""
        if not isinstance(data, dict):
            data = {}
        allowed = {f.name for f in fields(cls)}
        kwargs = {k: data[k] for k in data if k in allowed}
        return cls(**kwargs)


# normalizer / scraper 字段白名单（与 ListingSchema 字段一一对应）
LISTING_SCHEMA_FIELDS: list[str] = [f.name for f in fields(ListingSchema)]


def is_valid_listing_payload(data: dict) -> bool:
    """
    轻量入口校验：是否为 dict，且核心字段至少命中一项。
    非完整业务校验器。
    """
    if not isinstance(data, dict):
        return False

    def _present(key: str) -> bool:
        v = data.get(key)
        if v is None:
            return False
        if isinstance(v, str):
            return bool(v.strip())
        if isinstance(v, (int, float, bool)):
            return True
        return bool(v)

    core = ("rent_pcm", "postcode", "bedrooms", "source_url", "address")
    return any(_present(k) for k in core)


def convert_listing_schema_to_analyze_payload(
    listing: ListingSchema,
    *,
    budget: Optional[float] = None,
    target_postcode: Optional[str] = None,
) -> dict[str, Any]:
    """
    将标准房源转为当前 analyze / analyze-batch 单条 properties 所用 dict（web_bridge 兼容）。
    本阶段不自动接入路由；供后续 normalizer / API 调用。

    映射关系：
    - rent_pcm → rent
    - area_name → area
    - distance_miles → distance
    - commute_minutes / bedrooms / bills_included / postcode 同名或直传
    - budget / target_postcode 不在 schema 内，由参数可选传入
    """
    out: dict[str, Any] = {}
    if listing.rent_pcm is not None:
        out["rent"] = listing.rent_pcm
    if listing.bills_included is not None:
        out["bills_included"] = listing.bills_included
    if listing.commute_minutes is not None:
        out["commute_minutes"] = listing.commute_minutes
    if listing.bedrooms is not None:
        out["bedrooms"] = listing.bedrooms
    if listing.postcode:
        out["postcode"] = str(listing.postcode).strip() or None
    if listing.area_name:
        out["area"] = str(listing.area_name).strip() or None
    if listing.distance_miles is not None:
        out["distance"] = listing.distance_miles
    if listing.target_postcode_distance_miles is not None:
        # 引擎侧多为 distance；若同时有 distance_miles 已填则保留 distance 为主
        if "distance" not in out:
            out["distance"] = listing.target_postcode_distance_miles
    if budget is not None:
        out["budget"] = budget
    if target_postcode:
        out["target_postcode"] = str(target_postcode).strip() or None
    return {k: v for k, v in out.items() if v is not None}
