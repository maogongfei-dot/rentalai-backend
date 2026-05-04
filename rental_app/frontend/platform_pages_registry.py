"""Central registry of RentalAI page structure definitions (no DB, AI, or rendering)."""

from frontend.homepage_structure import get_homepage_structure
from frontend.listing_page_structure import get_listing_page_structure
from frontend.listing_detail_structure import get_listing_detail_structure
from frontend.map_page_structure import get_map_page_structure
from frontend.landlord_page_structure import get_landlord_page_structure
from frontend.account_page_structure import get_account_page_structure
from frontend.navigation_structure import get_navigation_structure
from frontend.contract_page_structure import get_contract_page_structure


def get_platform_pages_registry() -> dict:
    """Return navigation plus all page structures for downstream consumers."""
    return {
        "navigation": get_navigation_structure(),
        "pages": {
            "home": get_homepage_structure(),
            "long_rent_list": get_listing_page_structure("long_rent"),
            "short_rent_list": get_listing_page_structure("short_rent"),
            "listing_detail_long_rent": get_listing_detail_structure("long_rent"),
            "listing_detail_short_rent": get_listing_detail_structure("short_rent"),
            "listing_detail_external_short_rent": get_listing_detail_structure(
                "external_short_rent"
            ),
            "map": get_map_page_structure(),
            "landlord": get_landlord_page_structure(),
            "tenant_account": get_account_page_structure("tenant"),
            "landlord_account": get_account_page_structure("landlord"),
            "contract_analysis": get_contract_page_structure(),
        },
    }
