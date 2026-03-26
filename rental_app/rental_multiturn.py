# Phase C4：多轮上下文 — merge、follow-up intent、内存会话（无 DB、无 LLM）。
from __future__ import annotations

import copy
import re
import uuid
from typing import Any

from rental_query_parser import normalize_query_text

# 可选：进程内会话（重启即清空）；不传 conversation_id 时仍可仅用 previous_structured_query
CONVERSATION_STORE: dict[str, dict[str, Any]] = {}

# 参与「当前轮非 None 则覆盖」的标量键（与 parse_user_query 输出一致）
_MERGE_SCALAR_KEYS = (
    "city",
    "area",
    "postcode",
    "budget_min",
    "budget_max",
    "budget_flexible",
    "bedrooms",
    "room_type",
    "property_type",
    "bills_included",
    "furnished",
    "couple_friendly",
    "near_station",
    "commute_preference",
    "safety_priority",
    "quiet_priority",
)


def _dedupe_str_list(seq: list[str] | None) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for x in seq or []:
        s = str(x).strip()
        if not s or s in seen:
            continue
        seen.add(s)
        out.append(s)
    return out


def merge_structured_query(
    previous_query: dict[str, Any] | None,
    current_query: dict[str, Any] | None,
) -> dict[str, Any]:
    """
    上一轮 + 当前轮解析结果 → 合并后的 structured_query。
    规则：当前轮显式给出的字段（非 None）覆盖；未提及的保持旧值；
    notes / excluded_* 做并集；raw_user_query 使用当前轮原文便于展示。
    """
    prev = copy.deepcopy(previous_query) if previous_query else {}
    cur = copy.deepcopy(current_query) if current_query else {}
    out: dict[str, Any] = copy.deepcopy(prev)

    # budget_flexible：解析器在无「左右/around」时也会给 False，短句 follow-up 不应冲掉上一轮
    cur_has_budget = cur.get("budget_min") is not None or cur.get("budget_max") is not None

    for k in _MERGE_SCALAR_KEYS:
        if k == "budget_flexible":
            if cur_has_budget and k in cur and cur[k] is not None:
                out[k] = cur[k]
            continue
        if k in cur and cur[k] is not None:
            out[k] = cur[k]

    out["raw_user_query"] = (cur.get("raw_user_query") or "").strip() or prev.get(
        "raw_user_query", ""
    )

    out["notes"] = _dedupe_str_list(
        list(prev.get("notes") or []) + list(cur.get("notes") or [])
    )
    out["excluded_property_types"] = _dedupe_str_list(
        list(prev.get("excluded_property_types") or [])
        + list(cur.get("excluded_property_types") or [])
    )
    out["excluded_room_types"] = _dedupe_str_list(
        list(prev.get("excluded_room_types") or [])
        + list(cur.get("excluded_room_types") or [])
    )
    out["excluded_notes"] = _dedupe_str_list(
        list(prev.get("excluded_notes") or []) + list(cur.get("excluded_notes") or [])
    )

    return out


def detect_followup_intent(raw_user_query: str) -> dict[str, Any]:
    """
    轻量 rule-based：判断当前轮更像哪类 follow-up（供日志与策略参考）。
    优先级：重启搜索 > 排除 > 预算 > 位置 > 补充偏好 > 其它。
    """
    t = normalize_query_text(raw_user_query or "")

    if re.search(
        r"重新来|从头开始|重新开始|从头找|换.*重新|reset\b|start\s*over",
        t,
        re.IGNORECASE,
    ):
        return {"intent": "restart_search", "detail": None}

    if re.search(
        r"不要|别要|不想要|exclude|^no\s+\w+|不想合租|不想.*远",
        t,
        re.IGNORECASE,
    ):
        return {"intent": "exclude_option", "detail": None}

    if re.search(
        r"预算|改成|改为|调到|max\b|上限|以内|under\b|below\b|至少.*租",
        t,
        re.IGNORECASE,
    ):
        return {"intent": "update_budget", "detail": None}

    if re.search(r"换成|换到|改到|搬到|relocate|换城市", t, re.IGNORECASE):
        return {"intent": "update_location", "detail": None}

    if re.search(r"最好|希望|尽量|prefer|加上|还要|另外", t, re.IGNORECASE):
        return {"intent": "add_preference", "detail": None}

    return {"intent": "generic_followup", "detail": None}


def build_conversation_payload(
    *,
    conversation_id: str,
    turn_index: int,
    history: list[dict[str, Any]],
    current_structured_query: dict[str, Any],
    merged_query: dict[str, Any],
) -> dict[str, Any]:
    """稳定可序列化的会话快照（无 DB，结构与未来持久化对齐）。"""
    return {
        "conversation_id": conversation_id,
        "turn_index": turn_index,
        "history": history,
        "current_query": current_structured_query,
        "current_structured_query": current_structured_query,
        "merged_query": merged_query,
    }


def _ensure_conversation_id(conversation_id: str | None) -> str:
    if conversation_id and str(conversation_id).strip():
        return str(conversation_id).strip()
    return str(uuid.uuid4())


def update_conversation_store(
    conversation_id: str,
    *,
    raw_user_query: str,
    structured_query: dict[str, Any],
    merged_query: dict[str, Any],
) -> tuple[int, list[dict[str, Any]]]:
    """内存会话：追加一轮并保存最新 merged_query。"""
    cid = _ensure_conversation_id(conversation_id)
    if cid not in CONVERSATION_STORE:
        CONVERSATION_STORE[cid] = {"turn_index": 0, "history": [], "merged_query": None}

    CONVERSATION_STORE[cid]["turn_index"] = int(CONVERSATION_STORE[cid]["turn_index"]) + 1
    turn = CONVERSATION_STORE[cid]["turn_index"]
    entry = {
        "turn_index": turn,
        "raw_user_query": raw_user_query,
        "structured_query": copy.deepcopy(structured_query),
    }
    CONVERSATION_STORE[cid]["history"].append(entry)
    CONVERSATION_STORE[cid]["merged_query"] = copy.deepcopy(merged_query)
    CONVERSATION_STORE[cid]["last_raw"] = raw_user_query

    hist = copy.deepcopy(CONVERSATION_STORE[cid]["history"])
    return turn, hist
