"""Short-term rental listing data model (Phase 4-A1)."""


class ShortRentListing:
    def __init__(
        self,
        id: str,
        title: str,
        location: str,
        postcode: str,
        price_per_day: float,
        available_dates: list,
        min_days: int,
        max_days: int,
        landlord_id: str,
        description: str,
        created_at: str,
    ) -> None:
        self.id = id
        self.title = title
        self.location = location
        self.postcode = postcode
        self.price_per_day = price_per_day
        self.available_dates = available_dates
        self.min_days = min_days
        self.max_days = max_days
        self.landlord_id = landlord_id
        self.description = description
        self.created_at = created_at

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "location": self.location,
            "postcode": self.postcode,
            "price_per_day": self.price_per_day,
            "available_dates": self.available_dates,
            "min_days": self.min_days,
            "max_days": self.max_days,
            "landlord_id": self.landlord_id,
            "description": self.description,
            "created_at": self.created_at,
        }

    @staticmethod
    def from_dict(data: dict) -> "ShortRentListing":
        return ShortRentListing(
            id=data["id"],
            title=data["title"],
            location=data["location"],
            postcode=data["postcode"],
            price_per_day=data["price_per_day"],
            available_dates=data["available_dates"],
            min_days=data["min_days"],
            max_days=data["max_days"],
            landlord_id=data["landlord_id"],
            description=data["description"],
            created_at=data["created_at"],
        )
