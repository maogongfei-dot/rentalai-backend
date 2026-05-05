"""External short-term rental search result (SpareRoom, Rightmove, OpenRent, etc.)."""


class ExternalShortRentListing:
    def __init__(
        self,
        id: str,
        source: str,
        title: str,
        location: str,
        postcode: str,
        price_per_day: float,
        price_per_week: float,
        available_from: str,
        link: str,
        description: str,
        created_at: str,
    ) -> None:
        self.id = id
        self.source = source
        self.title = title
        self.location = location
        self.postcode = postcode
        self.price_per_day = price_per_day
        self.price_per_week = price_per_week
        self.available_from = available_from
        self.link = link
        self.description = description
        self.created_at = created_at

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "source": self.source,
            "title": self.title,
            "location": self.location,
            "postcode": self.postcode,
            "price_per_day": self.price_per_day,
            "price_per_week": self.price_per_week,
            "available_from": self.available_from,
            "link": self.link,
            "description": self.description,
            "created_at": self.created_at,
        }

    @staticmethod
    def from_dict(data: dict) -> "ExternalShortRentListing":
        return ExternalShortRentListing(
            id=data["id"],
            source=data["source"],
            title=data["title"],
            location=data["location"],
            postcode=data["postcode"],
            price_per_day=data["price_per_day"],
            price_per_week=data["price_per_week"],
            available_from=data["available_from"],
            link=data["link"],
            description=data["description"],
            created_at=data["created_at"],
        )
