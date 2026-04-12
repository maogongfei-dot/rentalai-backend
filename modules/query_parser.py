def extract_bedrooms(text: str):
    text = text.lower().strip()

    # 1. 特殊情况：studio / 自己住
    if (
        "studio" in text
        or "自己住" in text
        or "独住" in text
        or "private" in text
    ):
        return 0

    # 2. 合租 / 单间
    if (
        "合租" in text
        or "shared" in text
        or "share" in text
        or "single room" in text
        or "单间" in text
        or "单人间" in text
        or "1 room" in text
    ):
        return 1

    # 3. 中文 + 英文常见表达
    patterns = {
        1: [
            "一居", "1居", "一室", "1室",
            "1 bed", "one bed", "1 bedroom", "one bedroom", "1b"
        ],
        2: [
            "两居", "2居", "二居", "两室", "2室", "二室",
            "2 bed", "two bed", "2 bedroom", "two bedroom", "2b"
        ],
        3: [
            "三居", "3居", "三室", "3室",
            "3 bed", "three bed", "3 bedroom", "three bedroom", "3b"
        ],
        4: [
            "四居", "4居", "四室", "4室",
            "4 bed", "four bed", "4 bedroom", "four bedroom", "4b"
        ],
    }

    for bedrooms, keywords in patterns.items():
        for kw in keywords:
            if kw in text:
                return bedrooms

    return None