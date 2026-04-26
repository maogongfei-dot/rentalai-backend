"""
User reputation submission flow (in-memory, Phase 2 scaffold).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

ALLOWED_ENTITY_TYPES = {"address", "building", "agency", "landlord_private"}
ALLOWED_STATUSES = {"pending", "approved", "rejected"}

_SUBMISSIONS: list[dict[str, Any]] = []


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _validate_submission_input(data: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    entity_type = _clean_text(data.get("entity_type")).lower()
    entity_name = _clean_text(data.get("entity_name"))
    postcode = _clean_text(data.get("postcode"))
    address = _clean_text(data.get("address"))
    rating = data.get("rating")
    comment = _clean_text(data.get("comment"))

    if entity_type not in ALLOWED_ENTITY_TYPES:
        issues.append(
            "Please choose a valid entity type: address, building, agency, or landlord_private."
        )
    if not entity_name:
        issues.append("Please provide the property, building, agency, or landlord name.")
    if not address and not postcode:
        issues.append("Please add at least an address line or postcode.")
    if rating is None:
        issues.append("Please provide a rating from 1 to 5.")
    else:
        try:
            score = float(rating)
            if score < 1 or score > 5:
                issues.append("Rating should be between 1 and 5.")
        except (TypeError, ValueError):
            issues.append("Rating should be a number between 1 and 5.")
    if not comment:
        issues.append("Please add a short comment about your rental experience.")
    return issues


def _normalise_issue_tags(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    out: list[str] = []
    for item in value:
        tag = _clean_text(item).lower().replace(" ", "_")
        if tag and tag not in out:
            out.append(tag)
    return out[:10]


def create_reputation_submission(data: dict[str, Any]) -> dict[str, Any]:
    """
    Create a pending submission after lightweight field validation.
    """
    payload = data if isinstance(data, dict) else {}
    issues = _validate_submission_input(payload)
    if issues:
        return {
            "success": False,
            "message": "I still need a few details before I can save this submission.",
            "validation_issues": issues,
            "submission": {},
        }

    submission = {
        "submission_id": f"sub_{uuid4().hex[:12]}",
        "entity_type": _clean_text(payload.get("entity_type")).lower(),
        "entity_name": _clean_text(payload.get("entity_name")),
        "address": _clean_text(payload.get("address")),
        "postcode": _clean_text(payload.get("postcode")).upper(),
        "rating": round(float(payload.get("rating")), 1),
        "issue_tags": _normalise_issue_tags(payload.get("issue_tags")),
        "comment": _clean_text(payload.get("comment")),
        "evidence_note": _clean_text(payload.get("evidence_note")),
        "status": "pending",
        "created_at": _now_iso(),
    }
    _SUBMISSIONS.append(submission)
    return {
        "success": True,
        "message": "Thanks. Your feedback was submitted and is pending review.",
        "validation_issues": [],
        "submission": dict(submission),
    }


def review_reputation_submission(submission_id: str, action: str) -> dict[str, Any]:
    """
    Simulate manual moderation. Action: approve | reject.
    """
    sid = _clean_text(submission_id)
    act = _clean_text(action).lower()
    if not sid:
        return {
            "success": False,
            "message": "Please provide a submission ID.",
            "submission": {},
        }
    if act not in {"approve", "reject"}:
        return {
            "success": False,
            "message": "Action should be approve or reject.",
            "submission": {},
        }

    for item in _SUBMISSIONS:
        if item.get("submission_id") == sid:
            item["status"] = "approved" if act == "approve" else "rejected"
            return {
                "success": True,
                "message": f"Submission {sid} was marked as {item['status']}.",
                "submission": dict(item),
            }
    return {
        "success": False,
        "message": "I could not find that submission ID.",
        "submission": {},
    }


def list_public_reputation_submissions() -> list[dict[str, Any]]:
    """
    Return only approved records for public display.
    """
    out: list[dict[str, Any]] = []
    for item in _SUBMISSIONS:
        status = _clean_text(item.get("status")).lower()
        if status != "approved":
            continue
        if status not in ALLOWED_STATUSES:
            continue
        out.append(dict(item))
    return out

