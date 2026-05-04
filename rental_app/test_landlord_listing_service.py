from landlord.landlord_listing_service import prepare_landlord_listing_for_save


def test_create_long_rent_listing():
    data = {
        "landlord_id": "landlord_001",
        "title": "Modern 2 Bedroom Flat",
        "location": "London",
        "listing_mode": "long_rent",
        "monthly_price": 1800,
    }
    result = prepare_landlord_listing_for_save(data)
    listing = result["listing"]
    validation = result["validation"]

    assert validation["is_valid"] is True
    assert listing["source_type"] == "platform"
    assert listing["availability_status"] == "available"
    assert listing["listing_mode"] == "long_rent"


def test_create_short_rent_listing():
    data = {
        "landlord_id": "landlord_002",
        "title": "Short Stay Room",
        "location": "Manchester",
        "listing_mode": "short_rent",
        "price_per_night": 55,
        "min_stay_nights": 3,
        "cleaning_fee": 20,
    }
    result = prepare_landlord_listing_for_save(data)
    listing = result["listing"]
    validation = result["validation"]

    assert validation["is_valid"] is True
    assert listing["listing_mode"] == "short_rent"
    assert listing["price_per_night"] == 55


def test_invalid_listing_missing_price():
    data = {
        "landlord_id": "landlord_003",
        "title": "Invalid Listing",
        "location": "Leeds",
        "listing_mode": "long_rent",
    }
    result = prepare_landlord_listing_for_save(data)
    validation = result["validation"]

    assert validation["is_valid"] is False
    assert "monthly_price" in validation["missing_fields"]


if __name__ == "__main__":
    test_create_long_rent_listing()
    test_create_short_rent_listing()
    test_invalid_listing_missing_price()
    print("Landlord listing service tests passed.")
