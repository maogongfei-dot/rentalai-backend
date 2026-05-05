"""Short-term rental listings: JSON file storage under data/short_rent_listings.json."""

import json
from pathlib import Path

from backend.models.short_rent_model import ShortRentListing

_ROOT = Path(__file__).resolve().parent.parent.parent
_DATA_DIR = _ROOT / "data"
_JSON_PATH = _DATA_DIR / "short_rent_listings.json"


def load_short_rent_listings() -> list:
    if not _JSON_PATH.exists():
        return []
    text = _JSON_PATH.read_text(encoding="utf-8").strip()
    if not text:
        return []
    data = json.loads(text)
    if not isinstance(data, list):
        return []
    return [ShortRentListing.from_dict(item) for item in data]


def save_short_rent_listings(listings: list) -> None:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    payload = [x.to_dict() for x in listings]
    _JSON_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def add_short_rent_listing(listing: ShortRentListing) -> None:
    items = load_short_rent_listings()
    items.append(listing)
    save_short_rent_listings(items)
