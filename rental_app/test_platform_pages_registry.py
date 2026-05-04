from frontend.platform_pages_registry import get_platform_pages_registry


def test_platform_pages_registry():
    registry = get_platform_pages_registry()

    assert "navigation" in registry
    assert "pages" in registry

    pages = registry["pages"]

    required_pages = [
        "home",
        "long_rent_list",
        "short_rent_list",
        "listing_detail_long_rent",
        "listing_detail_short_rent",
        "listing_detail_external_short_rent",
        "map",
        "landlord",
        "tenant_account",
        "landlord_account",
        "contract_analysis",
    ]

    for page in required_pages:
        assert page in pages

    assert pages["home"]["main_buttons"]
    assert pages["landlord"]["publish_form"]
    assert pages["map"]["supported_listing_modes"]
    assert pages["contract_analysis"]["input_section"]

    print("Platform pages registry test passed.")


if __name__ == "__main__":
    test_platform_pages_registry()
