"""
Contract text parser (Phase 3 Part 1) — simple rules and keyword hits, no NLP.

Public API: ``parse_contract_text``.
"""

from __future__ import annotations

import json
import re
from typing import Any

CONTRACT_KEYWORDS: list[str] = [
    "rent",
    "deposit",
    "tenant",
    "landlord",
    "term",
    "notice",
    "termination",
    "repair",
    "maintenance",
]


def _empty_result() -> dict[str, Any]:
    return {
        "raw_text": "",
        "length": 0,
        "sections": [],
        "keywords": [],
        "entities": {
            "rent": None,
            "deposit": None,
            "term": None,
            "address": None,
        },
    }


def _split_sections(text: str) -> list[str]:
    """Split on newlines or full stops; strip and drop empties."""
    parts = re.split(r"[\.\n]+", text)
    return [p.strip() for p in parts if p.strip()]


def _extract_keywords(text_lower: str) -> list[str]:
    return [kw for kw in CONTRACT_KEYWORDS if kw in text_lower]


def _first_matching_sentence(sections: list[str], predicate) -> str | None:
    for s in sections:
        if predicate(s):
            return s
    return None


def _entity_rent(sections: list[str]) -> str | None:
    def pred(s: str) -> bool:
        sl = s.lower()
        return "£" in s or "rent" in sl

    return _first_matching_sentence(sections, pred)


def _entity_deposit(sections: list[str]) -> str | None:
    def pred(s: str) -> bool:
        return "deposit" in s.lower()

    return _first_matching_sentence(sections, pred)


def _entity_term(sections: list[str]) -> str | None:
    def pred(s: str) -> bool:
        sl = s.lower()
        return "month" in sl or "term" in sl

    return _first_matching_sentence(sections, pred)


def _entity_address(sections: list[str]) -> str | None:
    def pred(s: str) -> bool:
        return "address" in s.lower()

    return _first_matching_sentence(sections, pred)


def parse_contract_text(text: str) -> dict[str, Any]:
    """
    Parse a contract string into sections, keyword hits, and coarse entities.

    Non-string input is coerced with ``str()``; empty / whitespace-only input
    returns an empty-shaped result without raising.
    """
    raw = str(text) if not isinstance(text, str) else text
    if not raw.strip():
        return _empty_result()

    text_lower = raw.lower()
    sections = _split_sections(raw)
    keywords = _extract_keywords(text_lower)
    entities = {
        "rent": _entity_rent(sections),
        "deposit": _entity_deposit(sections),
        "term": _entity_term(sections),
        "address": _entity_address(sections),
    }
    return {
        "raw_text": raw,
        "length": len(raw),
        "sections": sections,
        "keywords": keywords,
        "entities": entities,
    }


def run_contract_parser_test() -> None:
    sample = (
        "This tenancy agreement includes a rent of £1200 per month. "
        "The deposit is £1200. The term is 12 months."
    )
    result = parse_contract_text(sample)
    print("length:", result["length"])
    print("keywords:", result["keywords"])
    # ASCII-safe for narrow consoles (e.g. Windows cp1252/gbk)
    print("entities:", json.dumps(result["entities"], ensure_ascii=True))


if __name__ == "__main__":
    run_contract_parser_test()
