from backend.app.map import get_location_info


def test_get_location_info_known_postcode():
    result = get_location_info("M1 4AB")
    assert result["status"] == "ok"
    assert result["city"] == "Manchester"
    assert "station" in result["transport_hint"].lower()


def test_get_location_info_known_address():
    result = get_location_info("22 Orchard Road, Bristol")
    assert result["status"] == "ok"
    assert result["postcode"] == "BS1 5TR"
    assert isinstance(result["nearby_points"], list) and result["nearby_points"]


def test_get_location_info_unknown():
    result = get_location_info("Some Unknown Address 123")
    assert result["status"] == "unknown"
    assert result["normalized_address"] == "Unknown"
    assert result["transport_hint"] == "Unknown"

