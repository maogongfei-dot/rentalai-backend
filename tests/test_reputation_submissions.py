from backend.app.reputation import (
    create_reputation_submission,
    list_public_reputation_submissions,
    review_reputation_submission,
)


def test_create_submission_with_missing_fields():
    result = create_reputation_submission({"entity_name": "Test Place"})
    assert result["success"] is False
    assert result["validation_issues"]
    assert result["submission"] == {}


def test_create_and_approve_submission_flow():
    created = create_reputation_submission(
        {
            "entity_type": "agency",
            "entity_name": "Test Lettings",
            "address": "99 Test Street",
            "postcode": "M1 1AA",
            "rating": 2.0,
            "issue_tags": ["deposit dispute", "poor communication"],
            "comment": "Deposit was delayed and replies were slow.",
            "evidence_note": "Email thread available.",
        }
    )
    assert created["success"] is True
    sid = created["submission"]["submission_id"]
    assert created["submission"]["status"] == "pending"

    # Pending feedback should not be public yet.
    pending_public = list_public_reputation_submissions()
    assert all(x["submission_id"] != sid for x in pending_public)

    reviewed = review_reputation_submission(sid, "approve")
    assert reviewed["success"] is True
    assert reviewed["submission"]["status"] == "approved"

    approved_public = list_public_reputation_submissions()
    assert any(x["submission_id"] == sid for x in approved_public)


def test_review_reject_and_invalid_action():
    created = create_reputation_submission(
        {
            "entity_type": "building",
            "entity_name": "Sample Court",
            "address": "10 Sample Road",
            "postcode": "LS1 1AA",
            "rating": 3.0,
            "issue_tags": [],
            "comment": "Average experience.",
            "evidence_note": "",
        }
    )
    sid = created["submission"]["submission_id"]
    bad_action = review_reputation_submission(sid, "hold")
    assert bad_action["success"] is False

    rejected = review_reputation_submission(sid, "reject")
    assert rejected["success"] is True
    assert rejected["submission"]["status"] == "rejected"

