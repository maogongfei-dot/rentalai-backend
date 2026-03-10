import json

def show_listings(listings):
    if not listings:
        print("暂无房源。")
        return
    print("\n当前房源列表：")
    for i, item in enumerate(listings, start=1):
        rent = item.get("rent", "N/A")
        area = item.get("area", "N/A")
        bills = item.get("bills_included", "N/A")
        distance = item.get("distance", "N/A")
        distance_score = item.get("distance_score", 0)

        print(f"{i}. area={area} | rent={rent} | bills_included={bills} | distance={distance} | distance_score={distance_score}")

def ask_yes_no(prompt):
    while True:
        s = input(prompt).strip().lower()
        if s in ["y", "yes"]:
            return True
        if s in ["n", "no"]:
            return False
        print("❌ 请输入 y/n")

def show_stats(houses):
    if not houses:
        print("当前没有房源可统计。")
        return

    # 兼容 rent 可能是 "1200" / "£1200" / "1200pcm" 之类
    rents = []
    for h in houses:
        r = str(h.get("rent", "")).strip()
        r = r.replace("£", "").replace(",", "")
        # 只保留数字
        num = "".join(ch for ch in r if ch.isdigit())
        if num:
            rents.append(int(num))

    print(f"房源总数：{len(houses)}")
    if rents:
        print(f"可用租金数：{len(rents)}")
        print(f"平均租金：{sum(rents)/len(rents):.0f}")
        print(f"最低租金：{min(rents)}")
        print(f"最高租金：{max(rents)}")
    else:
        print("租金字段无法解析为数字（请检查 rent 的格式）。")

def ask_choice(prompt, allowed):
    allowed = [str(x) for x in allowed]
    while True:
        s = input(prompt).strip()
        if s in allowed:
            return s
        print(f"❌ 请输入 {', '.join(allowed)} 其中一个")

def ask_int(prompt, min_val=None, max_val=None):
    while True:
        s = input(prompt).strip()
        if not s.isdigit():
            print("❌ 请输入纯数字")
            continue
        v = int(s)
        if min_val is not None and v < min_val:
            print(f"❌ 不能小于 {min_val}")
            continue
        if max_val is not None and v > max_val:
            print(f"❌ 不能大于 {max_val}")
            continue
        return v

def explain_house(h):
    r = parse_rent(h.get("rent"))
    bills = str(h.get("bills", "")).strip().lower()
    area = str(h.get("area", "")).strip()

    parts = []

    # 价格解释（要和 score_house 的分档一致）
    if r is None:
        parts.append("租金未知+0")
    elif r <= 800:
        parts.append("租金<=800 +30")
    elif r <= 1000:
        parts.append("租金<=1000 +25")
    elif r <= 1200:
        parts.append("租金<=1200 +18")
    elif r <= 1500:
        parts.append("租金<=1500 +10")
    else:
        parts.append("租金>1500 +5")

    bills_yes = bills in ("y", "yes", "true", "1", "包", "包含")
    parts.append("包bill +15" if bills_yes else "不包bill +0")

    parts.append("有area +5" if area else "无area +0")

    return "；".join(parts)

def parse_rent(value):
    s = str(value).strip().replace("£", "").replace(",", "")
    num = "".join(ch for ch in s if ch.isdigit())
    return int(num) if num else None

if __name__ == "__main__":
    import json

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent          # rental_app 目录
HOUSES_PATH = BASE_DIR.parent / "houses.json"       # python_learning/houses.json

#with open(HOUSES_PATH, "r", encoding="utf-8") as f:
#    houses = json.load(f)

#    from module2_scoring import rank_houses

#    prefs = {}
#    weights = {}

#   results = rank_houses(houses, prefs, weights)

#for r in results:
#    d = r["area_detail"]
#    print("postcode:", d.get("postcode"))
#   print("base_score:", d.get("base_score"))
#    print("area_score:", d.get("area_score"), " weight:", d.get("area_weight"), " add:", d.get("area_add"))
#    print("final_score:", d.get("final_score"))
#    print("base_detail:", r.get("base_detail"))
#    print("area_detail:", r.get("area_detail"))
#    print("------")