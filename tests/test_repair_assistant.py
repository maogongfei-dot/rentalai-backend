from backend.app.repair import build_repair_guidance


def test_repair_guidance_urgent_damage():
    result = build_repair_guidance(
        "There is a leak and water damage in my flat for 2 days. I emailed landlord yesterday."
    )
    assert result["issue_type"] == "urgent_damage"
    assert "urgent" in result["situation"].lower()
    assert result["what_to_do_now"]
    assert "Hi [Landlord/Agent]" in result["message_template"]


def test_repair_guidance_landlord_not_responding():
    result = build_repair_guidance(
        "Boiler broken for 1 week. I contacted landlord twice and landlord not responding."
    )
    assert result["issue_type"] in ("landlord_not_responding", "delay", "repair_issue")
    assert result["if_no_response"]


def test_repair_guidance_insufficient_detail():
    result = build_repair_guidance("Need help with repair.")
    assert "I need a bit more detail about the issue" in result["situation"]
    assert result["message_template"] == ""

