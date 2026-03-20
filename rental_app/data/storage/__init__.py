# P3 Phase3: 本地 JSON 房源存储
from .listing_storage import (
    DEFAULT_LISTINGS_PATH,
    export_listings_as_dicts,
    get_listing_by_id,
    load_listings,
    load_listings_by_source,
    save_listing,
    save_listings,
)

__all__ = [
    "DEFAULT_LISTINGS_PATH",
    "export_listings_as_dicts",
    "get_listing_by_id",
    "load_listings",
    "load_listings_by_source",
    "save_listing",
    "save_listings",
]
