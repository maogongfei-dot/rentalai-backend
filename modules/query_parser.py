def extract_bedrooms(text: str):
    text = text.lower()

    # 1️⃣ 特殊情况
    if "studio" in text:
        return 0

    if "single room" in text or "1 room" in text:
        return 1

    # 2️⃣ 常见表达
    patterns = {
        1: ["1 bed", "one bed", "1 bedroom", "one bedroom", "1b"],
        2: ["2 bed", "two bed", "2 bedroom", "two bedroom", "2b"],
        3: ["3 bed", "three bed", "3 bedroom", "three bedroom", "3b"],
        4: ["4 bed", "four bed", "4 bedroom", "four bedroom", "4b"],
    }

    for bedrooms, keywords in patterns.items():
        for kw in keywords:
            if kw in text:
                return bedrooms

    return None