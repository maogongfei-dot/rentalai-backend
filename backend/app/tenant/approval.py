"""
Lightweight tenant suitability estimator (no credit API, rules only).
"""

from __future__ import annotations

import re
from typing import Any

INSUFFICIENT_DETAIL_TEXT = (
    "I need a bit more detail to estimate your approval chances. "
    "You can share income, job status, or whether you have a guarantor."
)


def _normalize(text: str) -> str:
    return " ".join((text or "").lower().split())


def _extract_income(text: str) -> int | None:
    m = re.search(r"£\s*(\d{3,6})", text)
    if m:
        return int(m.group(1))
    m2 = re.search(r"\b(\d{4,6})\s*(?:per month|pcm|monthly)\b", text, flags=re.I)
    if m2:
        return int(m2.group(1))
    return None


def estimate_approval_chance(user_text: str) -> dict[str, Any]:
    """
    Estimate approval likelihood from user-provided context only.
    """
    low = _normalize(user_text)
    income = _extract_income(user_text or "")
    has_worker = any(x in low for x in ("worker", "full-time", "employed", "job"))
    has_student = "student" in low
    has_guarantor = any(x in low for x in ("guarantor", "guarantee"))
    has_upfront = any(
        x in low
        for x in (
            "upfront",
            "in advance",
            "6 months",
            "six months",
            "pay 3 months",
            "pay three months",
        )
    )
    visa_note = ""
    if any(x in low for x in ("visa", "brp", "right to rent", "immigration status")):
        visa_note = "Visa or status documents may be requested."

    signal_count = sum(
        [
            1 if income is not None else 0,
            1 if (has_worker or has_student) else 0,
            1 if has_guarantor else 0,
            1 if has_upfront else 0,
        ]
    )
    if signal_count < 2:
        return {
            "approval_chance": "Unknown",
            "why": [INSUFFICIENT_DETAIL_TEXT],
            "how_to_improve": [
                "add guarantor",
                "offer upfront rent",
                "provide payslips",
            ],
            "insufficient_detail_message": INSUFFICIENT_DETAIL_TEXT,
            "signals": {
                "income": income,
                "student_or_worker": "student" if has_student else ("worker" if has_worker else ""),
                "has_guarantor": has_guarantor,
                "has_upfront_payment": has_upfront,
                "visa_note": visa_note,
            },
        }

    score = 0
    reasons: list[str] = []
    improvements: list[str] = []

    if income is not None:
        if income >= 2600:
            score += 2
            reasons.append("Income signal looks stronger for typical affordability checks.")
        elif income >= 1800:
            score += 1
            reasons.append("Income may be workable, but some landlords may ask for extra proof.")
        else:
            score -= 1
            reasons.append("Income signal looks tighter, so checks may be stricter.")
            improvements.append("provide payslips")
    else:
        improvements.append("share monthly income")

    if has_worker:
        score += 1
        reasons.append("Employment status usually helps with landlord approval.")
    elif has_student:
        reasons.append("Student applications are possible, but often need stronger supporting documents.")
        improvements.append("add guarantor")
    else:
        improvements.append("share job status")

    if has_guarantor:
        score += 1
        reasons.append("Having a guarantor can reduce landlord risk concerns.")
    else:
        improvements.append("add guarantor")

    if has_upfront:
        score += 1
        reasons.append("Offering upfront rent can improve approval likelihood.")
    else:
        improvements.append("offer upfront rent")

    if visa_note:
        reasons.append(visa_note)
        improvements.append("prepare right-to-rent documents")

    if score >= 4:
        chance = "High"
    elif score >= 2:
        chance = "Medium"
    else:
        chance = "Low"

    # De-duplicate suggestions while preserving order.
    dedup_improvements: list[str] = []
    for item in improvements:
        if item and item not in dedup_improvements:
            dedup_improvements.append(item)

    return {
        "approval_chance": chance,
        "why": reasons[:4] if reasons else [INSUFFICIENT_DETAIL_TEXT],
        "how_to_improve": dedup_improvements[:5] if dedup_improvements else ["provide payslips"],
        "insufficient_detail_message": "",
        "signals": {
            "income": income,
            "student_or_worker": "student" if has_student else ("worker" if has_worker else ""),
            "has_guarantor": has_guarantor,
            "has_upfront_payment": has_upfront,
            "visa_note": visa_note,
        },
    }

