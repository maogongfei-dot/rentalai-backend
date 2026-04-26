from backend.app.chat.router import handle_chat_request


def test_landlord_mode_detected_and_rendered():
    result = handle_chat_request("I am a landlord and I want to rent out my flat.")
    sections = result.get("display_sections") or {}
    assert sections.get("user_role") == "landlord"
    support = sections.get("landlord_support") or []
    assert support
    assert "You appear to be a landlord." in support[0]


def test_tenant_mode_default():
    result = handle_chat_request("I am looking for a flat near M1 4AB.")
    sections = result.get("display_sections") or {}
    assert sections.get("user_role") in ("tenant", "")
    support = sections.get("landlord_support") or []
    assert support == []

