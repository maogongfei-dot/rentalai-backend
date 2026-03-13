from module5_area.area_service import AreaService
from module2_scoring import calculate_area_preference_score

# AreaService (existing)
svc = AreaService()
print(svc.get_area("E1 6AN"))
print(svc.get_area("SW11 2AA"))

# Module5 Phase2: area preference score 最小可运行示例
def test_area_preference_score():
    settings = {
        "preferred_areas": ["bedford", "  MK40  "],
        "avoided_areas": ["zone_x"],
        "preferred_postcodes": ["mk41 1ab", "e1 6an"],
    }
    # 1) preferred area 命中
    h1 = {"area": "Bedford", "postcode": "NN1 2AB"}
    score1, reason1 = calculate_area_preference_score(h1, settings)
    assert score1 >= 8, "preferred area 应得高分"
    print(f"preferred area 命中: score={score1}, reason={reason1}")

    # 2) avoided area 命中
    h2 = {"area": "Zone_X", "postcode": "ZZ9 9ZZ"}
    score2, reason2 = calculate_area_preference_score(h2, settings)
    assert score2 <= 3, "avoided area 应得低分"
    print(f"avoided area 命中: score={score2}, reason={reason2}")

    # 3) preferred postcode 命中
    h3 = {"area": "Other", "postcode": "E1 6AN"}
    score3, reason3 = calculate_area_preference_score(h3, settings)
    assert score3 >= 8, "preferred postcode 应得高分"
    print(f"preferred postcode 命中: score={score3}, reason={reason3}")

    # 4) 无偏好设置 / 缺失字段 -> 中性分
    score4, _ = calculate_area_preference_score({"area": None, "postcode": None}, {})
    assert score4 == 5.0
    print("缺失/未设置: 中性分 5.0 OK")


if __name__ == "__main__":
    test_area_preference_score()