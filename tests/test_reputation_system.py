from backend.app.reputation import analyze_reputation


def test_analyze_reputation_known_agency_high_risk():
    result = analyze_reputation("NorthBridge Lettings")
    assert result["reputation_level"] == "High Risk"
    assert "deposit_dispute" in result["risk_tags"]
    assert isinstance(result["suggested_action"], str) and result["suggested_action"]


def test_analyze_reputation_known_building_low_or_medium():
    result = analyze_reputation("Maple Court")
    assert result["reputation_level"] in ("Low Risk", "Medium Risk")
    assert result["entity"]["entity_type"] == "building"
    assert result["source"] == "mock_seed"


def test_analyze_reputation_unknown_entity():
    result = analyze_reputation("Unknown Place 999")
    assert result["reputation_level"] == "Unknown"
    assert result["risk_tags"] == []
    assert "do not have reputation data" in result["summary"].lower()

