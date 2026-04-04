"""Bridge contract analysis outputs to the legal compliance module (Phase 0 Step 4)."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

# Allow `from backend.app.legal...` when rental_app runs with cwd != repo root.
_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from backend.app.legal.compliance_engine import analyze_legal_compliance
from backend.app.legal.compliance_types import LegalInput
from backend.app.legal.legal_result_builder import (
    build_empty_legal_response,
    build_error_legal_response,
    build_legal_analysis_response,
)

_SKIP_KEYS = frozenset({"legal_compliance"})
_TEXT_SCALAR_KEYS = frozenset(
    {
        "clause_text",
        "extracted_text",
        "raw_text",
        "matched_text",
        "summary",
        "text",
        "plaintext",
        "body",
        "clause",
        "content",
        "short_clause_preview",
        "overall_conclusion",
        "key_risk_summary",
        "risk_title",
        "short_advice",
        "plain_text",
        "location_hint",
        "short_summary",
    }
)


def extract_legal_text_from_contract_result(contract_result: Any) -> str:
    """Collect human-readable text from a contract analysis tree for legal screening."""
    if contract_result is None:
        return ""
    if isinstance(contract_result, str):
        return contract_result.strip()
    if isinstance(contract_result, dict):
        if "analysis_result" in contract_result or "structured_analysis" in contract_result:
            ar = contract_result.get("analysis_result") or contract_result.get("structured_analysis")
            er = contract_result.get("explain_result") or contract_result.get("explain")
            pr = contract_result.get("presentation")
            chunks: list[str] = []
            if ar is not None:
                chunks.append(extract_legal_text_from_contract_result(ar))
            if er is not None:
                chunks.append(extract_legal_text_from_contract_result(er))
            if pr is not None:
                chunks.append(extract_legal_text_from_contract_result(pr))
            return "\n\n".join(c for c in chunks if c)
        parts: list[str] = []
        for k, v in contract_result.items():
            if k in _SKIP_KEYS:
                continue
            if k in _TEXT_SCALAR_KEYS and isinstance(v, str) and v.strip():
                parts.append(v.strip())
            elif isinstance(v, (dict, list)):
                sub = extract_legal_text_from_contract_result(v)
                if sub:
                    parts.append(sub)
        return "\n\n".join(parts) if parts else ""
    if isinstance(contract_result, list):
        pieces = [extract_legal_text_from_contract_result(x) for x in contract_result]
        return "\n\n".join(p for p in pieces if p)
    return ""


def run_legal_compliance_from_text(
    text: str,
    jurisdiction: str = "england",
    target_date: str | None = None,
    source_type: str = "contract_clause",
) -> dict[str, Any]:
    """Run local legal compliance pipeline and return the canonical response dict."""
    try:
        if not (text or "").strip():
            return build_empty_legal_response(
                jurisdiction=jurisdiction,
                source_type=source_type,
            )
        payload = LegalInput(
            text=text.strip(),
            rule_ids=None,
            jurisdiction=jurisdiction,
            target_date=target_date,
            source_type=source_type,
        )
        analysis = analyze_legal_compliance(payload)
        return build_legal_analysis_response(analysis)
    except Exception as exc:
        return build_error_legal_response(
            str(exc),
            jurisdiction=jurisdiction,
            source_type=source_type,
        )


def attach_legal_compliance_to_result(
    base_result: Any,
    jurisdiction: str = "england",
    target_date: str | None = None,
    source_type: str = "contract_clause",
) -> dict[str, Any]:
    """Attach ``legal_compliance`` to a contract analysis result dict without dropping fields."""
    try:
        if isinstance(base_result, dict):
            out: dict[str, Any] = dict(base_result)
        else:
            out = {"value": base_result}
        text = extract_legal_text_from_contract_result(out)
        out["legal_compliance"] = run_legal_compliance_from_text(
            text,
            jurisdiction=jurisdiction,
            target_date=target_date,
            source_type=source_type,
        )
        return out
    except Exception as exc:
        if isinstance(base_result, dict):
            out = dict(base_result)
        else:
            out = {"value": base_result}
        out["legal_compliance"] = build_error_legal_response(
            str(exc),
            jurisdiction=jurisdiction,
            source_type=source_type,
        )
        return out
