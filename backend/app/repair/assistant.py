"""
Repair / tenant-rights guidance helper (rule-based, no external systems).
"""

from __future__ import annotations

from typing import Any

INSUFFICIENT_DETAIL_TEXT = (
    "I need a bit more detail about the issue (e.g. what is broken, how long it has been, whether you contacted the landlord)."
)


def _normalize(text: str) -> str:
    return " ".join((text or "").lower().split())


def _issue_type(low: str) -> str:
    if any(x in low for x in ("leak", "flood", "water damage", "mould", "mold", "no heating", "gas smell", "electrical")):
        return "urgent_damage"
    if any(x in low for x in ("landlord not replying", "landlord not responding", "no reply", "ignored", "not responding")):
        return "landlord_not_responding"
    if any(x in low for x in ("delay", "delayed", "waiting", "still not fixed", "been weeks")):
        return "delay"
    if any(x in low for x in ("broken", "repair", "fix", "boiler", "heating", "toilet", "door", "window", "damp")):
        return "repair_issue"
    return "unknown"


def _build_template(issue_summary: str) -> str:
    return (
        "Hi [Landlord/Agent],\n\n"
        f"I am writing to report a repair issue: {issue_summary}. "
        "The issue started on [date] and it is affecting normal use of the property.\n\n"
        "Please confirm in writing when this will be inspected and repaired. "
        "I can provide photos/videos if needed.\n\n"
        "Thanks,\n"
        "[Your name]"
    )


def build_repair_guidance(user_text: str) -> dict[str, Any]:
    """
    Return practical repair/escalation guidance from user description.
    """
    text = (user_text or "").strip()
    low = _normalize(text)
    issue = _issue_type(low)
    has_time = any(x in low for x in ("day", "days", "week", "weeks", "month", "months", "since"))
    has_contact = any(x in low for x in ("called", "messaged", "emailed", "contacted", "reported"))
    has_broken_detail = any(
        x in low
        for x in ("leak", "heating", "boiler", "toilet", "mould", "mold", "window", "door", "electric", "water")
    )

    if issue == "unknown" and not has_broken_detail:
        return {
            "issue_type": "unknown",
            "situation": INSUFFICIENT_DETAIL_TEXT,
            "what_to_do_now": [],
            "message_template": "",
            "if_no_response": [],
            "insufficient_detail_message": INSUFFICIENT_DETAIL_TEXT,
        }

    if (not has_time or not has_contact) and issue in ("repair_issue", "delay", "landlord_not_responding"):
        return {
            "issue_type": issue,
            "situation": INSUFFICIENT_DETAIL_TEXT,
            "what_to_do_now": [],
            "message_template": "",
            "if_no_response": [],
            "insufficient_detail_message": INSUFFICIENT_DETAIL_TEXT,
        }

    if issue == "urgent_damage":
        situation = "This looks like an urgent repair or safety issue."
        now_steps = [
            "Take photos/videos and note the date/time now.",
            "Report it to the landlord or agent immediately in writing.",
            "If there is active danger (e.g. gas/electrical), contact emergency services or relevant hotline.",
        ]
        no_response = [
            "Send a same-day written follow-up marked as urgent.",
            "Contact your local council housing team if safety risk continues.",
            "Keep all evidence and communication logs.",
        ]
    elif issue == "landlord_not_responding":
        situation = "You have reported the issue, but the landlord or agent is not responding."
        now_steps = [
            "Send a clear written follow-up with issue details and timeline.",
            "Ask for a repair date and written confirmation.",
            "Keep screenshots/emails and a dated repair log.",
        ]
        no_response = [
            "Escalate with a formal written notice.",
            "Contact your local council tenancy/housing advice team.",
            "Ask a tenant support service for next legal-safe steps.",
        ]
    elif issue == "delay":
        situation = "The repair appears delayed beyond a reasonable timeframe."
        now_steps = [
            "Send a written reminder with dates of earlier reports.",
            "Request a specific inspection and fix date.",
            "Record ongoing impact (photos, temperature, access issues).",
        ]
        no_response = [
            "Escalate in writing and mention the unresolved delay.",
            "Seek council or tenant advice support.",
            "Keep all records in case formal escalation is needed.",
        ]
    else:
        situation = "This looks like a standard repair issue that needs clear written follow-up."
        now_steps = [
            "Describe what is broken and when it started.",
            "Report it in writing and ask for a repair timescale.",
            "Keep photos and written records.",
        ]
        no_response = [
            "Send one more formal follow-up with dates.",
            "Escalate to local housing advice if still unresolved.",
        ]

    issue_summary = text if len(text) <= 180 else text[:177].rstrip() + "..."
    return {
        "issue_type": issue,
        "situation": situation,
        "what_to_do_now": now_steps,
        "message_template": _build_template(issue_summary),
        "if_no_response": no_response,
        "insufficient_detail_message": "",
    }

