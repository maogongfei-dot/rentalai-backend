import json
from pathlib import Path

def get_london_zone(postcode: str):
    postcode = postcode.upper()

    if postcode.startswith(("E", "EC", "WC")):
        return 1
    if postcode.startswith(("N", "NW", "SE", "SW")):
        return 2
    if postcode.startswith(("W",)):
        return 2
    if postcode.startswith(("CR", "BR", "DA")):
        return 4
    if postcode.startswith(("RM", "EN", "UB")):
        return 5
    return 5

def normalize_area_key(value: str) -> str:
    """
    输入可以是：
    - postcode: "E1 6AN" / "SW11 2AA" / "M1 1AE"
    - 或者你临时用的 area: "A"
    输出：用于 areas.json 的 key
    规则：取第一个空格前的 outward code
    """
    if not value:
        return ""
    s = str(value).strip().upper()
    if not s:
        return ""
    return s.split()[0]  # "E1 6AN" -> "E1"

class AreaService:
    def __init__(self, path="data/areas.json"):
        self.path = Path(path)
        self.load()

    def load(self):
        if not self.path.exists():
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text("{}", encoding="utf-8")

        with open(self.path, "r", encoding="utf-8") as f:
            self.data = json.load(f)

    def save(self):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def get_area(self, postcode_or_area: str, refresh: bool = False):
        area_id = normalize_area_key(postcode_or_area)

        if refresh or area_id not in self.data:
            zone = get_london_zone(postcode_or_area)
            zone_score = {1:95, 2:85, 3:75, 4:65, 5:55}

            self.data[area_id] = {
                "safety": 3,
                "transport": 3,
                "amenities": 3,
                "cost": 3,
                "noise": 3,
                "area_score": zone_score.get(zone, 55)
            }
            self.save()

        return self.data[area_id]