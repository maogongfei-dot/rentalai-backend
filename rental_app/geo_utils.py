import math


def postcode_to_coord(postcode):
    """
    简化版 postcode → 坐标
    这里只做测试用，后期会换 API
    """

    fake_coords = {
        "MK40": (52.1364, -0.4666),
        "MK41": (52.1500, -0.4500),
        "MK42": (52.1200, -0.4700),
        "E1": (51.5200, -0.0600),
        "SW1": (51.5000, -0.1400)
    }

    return fake_coords.get(postcode.upper())


def haversine(lat1, lon1, lat2, lon2):
    """
    计算两点之间 miles
    """

    R = 3958.8  # Earth radius in miles

    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


def calculate_distance(postcode1, postcode2):
    try:
        if not postcode1 or not postcode2:
            return None
        
        postcode1 = normalize_postcode(postcode1)
        postcode2 = normalize_postcode(postcode2)

        if not postcode1 or not postcode2:
            return None
        
        coord1 = postcode_to_coord(postcode1)
        coord2 = postcode_to_coord(postcode2)

        if not coord1 or not coord2:
            return None
        
        lat1, lon1 = coord1
        lat2, lon2 = coord2

    except Exception:
        return None
    
    return round(haversine(lat1, lon1, lat2, lon2), 2)

def get_final_distance(house, target_postcode):
    """
    Priority:
    1. use existing manual distance if valid
    2. auto-calculate from postcode
    3. fallback to None
    """
    existing_distance = house.get("distance")

    if isinstance(existing_distance, (int, float)) and existing_distance >= 0:
        return round(float(existing_distance), 2)

    house_postcode = house.get("postcode")
    if not house_postcode or not target_postcode:
        return None

    try:
        distance = calculate_distance(house_postcode, target_postcode)
        if distance is None:
            return None
        return round(float(distance), 2)
    except Exception:
        return None
    
def normalize_postcode(postcode):
    if not postcode:
        return None
    postcode = str(postcode).strip().upper()
    return postcode if postcode else None