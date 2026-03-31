"""
Part 7：轻量条款切分（无 NLP），供 ``clause_list`` 使用。

规则优先级：空行分段 → 段内编号行（1. / 2.）→ 过长段按句末标点拆句。
"""

from __future__ import annotations

import re
from typing import Any

_RE_BLANK_PARA = re.compile(r"\n\s*\n+")
# 行首编号：1. / 2) / 3： 等
_RE_NUMBERED_LINE = re.compile(r"(?m)^\s*\d+[\.\)\：:]\s+")

# 单段过长时再拆句
_MAX_PARA_CHARS = 380
_MAX_CLAUSES = 200


def _split_long_paragraph(p: str) -> list[str]:
    p = p.strip()
    if len(p) <= _MAX_PARA_CHARS:
        return [p]
    parts = re.split(r"(?<=[.!?。！？])\s+", p)
    parts = [x.strip() for x in parts if x.strip()]
    if len(parts) <= 1:
        return [p]
    return parts


def _split_numbered_block(p: str) -> list[str] | None:
    """
    若存在至少一行「行首编号」，则按编号边界切段；仅一处编号时整段保留为一条。
    无编号行则返回 None，交由上层按长度处理。
    """
    p = p.strip()
    if not p:
        return None
    matches = list(_RE_NUMBERED_LINE.finditer(p))
    if not matches:
        return None
    if len(matches) == 1:
        return [p.strip()]
    chunks: list[str] = []
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(p)
        chunks.append(p[start:end].strip())
    return chunks


def parse_contract_clauses(contract_text: str) -> list[dict[str, Any]]:
    """
    将合同正文拆为条款列表；每条默认 ``clause_type=general``，``matched_keywords`` / ``risk_flags`` 为空。

    返回的 dict 经 ``_normalize_clause_dict`` 后写入 ``ContractAnalysisResult.clause_list``。
    """
    t = (contract_text or "").strip()
    if not t:
        return []

    paragraphs = [x.strip() for x in _RE_BLANK_PARA.split(t) if x.strip()]
    if not paragraphs:
        paragraphs = [t]

    raw: list[str] = []
    for para in paragraphs:
        if not para.strip():
            continue
        numbered = _split_numbered_block(para)
        if numbered is not None:
            raw.extend(numbered)
            continue
        if len(para) > _MAX_PARA_CHARS:
            raw.extend(_split_long_paragraph(para))
        else:
            raw.append(para.strip())

    raw = [c.strip() for c in raw if c and len(c.strip()) >= 2]
    raw = raw[:_MAX_CLAUSES]

    out: list[dict[str, Any]] = []
    for i, chunk in enumerate(raw):
        n = i + 1
        cid = f"clause_{n}"
        out.append(
            {
                "clause_id": cid,
                "clause_text": chunk,
                "clause_type": "general",
                "matched_keywords": [],
                "risk_flags": [],
                "location_hint": cid,
            }
        )
    return out


def split_contract_into_clauses(contract_text: str) -> list[dict[str, Any]]:
    """与 ``parse_contract_clauses`` 同义，便于按「split」语义调用。"""
    return parse_contract_clauses(contract_text)
