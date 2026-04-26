from backend.app.tenant import estimate_approval_chance


def test_estimate_approval_chance_high_signal():
    result = estimate_approval_chance(
        "I am a full-time worker, income £3200 per month, have a guarantor and can pay 6 months upfront."
    )
    assert result["approval_chance"] in ("High", "Medium")
    assert isinstance(result["why"], list) and result["why"]
    assert isinstance(result["how_to_improve"], list)


def test_estimate_approval_chance_unknown_when_sparse():
    result = estimate_approval_chance("Can I pass?")
    assert result["approval_chance"] == "Unknown"
    assert "I need a bit more detail to estimate your approval chances." in result["why"][0]


def test_estimate_approval_chance_student_without_support():
    result = estimate_approval_chance("I am a student and no guarantor for now.")
    assert result["approval_chance"] in ("Unknown", "Low", "Medium")
    assert any("guarantor" in x for x in [s.lower() for s in result["how_to_improve"]])

