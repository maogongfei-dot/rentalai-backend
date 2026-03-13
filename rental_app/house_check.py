import json
import csv
from geo_utils import calculate_distance
from geo_utils import get_final_distance
# UI
from ui import (
    show_listings,
    show_stats,
    ask_yes_no,
    ask_choice,
    ask_int,
    explain_house,
    parse_rent
)

# Actions
from actions import (
    delete_listing,
    edit_listing,
    clear_listings,
    strip_scores
)

# Scoring
from scoring_adapter import get_top_n, explain_score

# Module3: Contract risk (demo only, not in final_score)
from contract_risk import calculate_contract_risk_score, calculate_structured_risk_score

# State
from state import init_state, save_state, load_state

print("### RUNNING house_check.py VERSION A (2026-02-27) ###")

# def save_data(houses, filepath="houses.json"):
#     with open(filepath, "w", encoding="utf-8") as f:
#         json.dump(houses, f, ensure_ascii=False, indent=2)
#     print(f"✅ 已保存 {len(houses)} 条房源到 {filepath}")

# def load_data(filepath="houses.json"):
#     try:
#         with open(filepath, "r", encoding="utf-8") as f:
#             houses = json.load(f)
#         if not isinstance(houses, list):
#             print("❌ 文件格式不对（不是列表），已返回空列表")
#             return []
#         print(f"✅ 已加载 {len(houses)} 条房源：{filepath}")
#         return houses
#     except FileNotFoundError:
#         print(f"❌ 找不到文件：{filepath}（先用 4 保存一次）")
#         return []
#     except json.JSONDecodeError:
#         print("❌ 文件不是合法 JSON（可能被你手动改坏了）")
#         return []


def export_to_csv(listings, filename="houses.csv"):
    if not listings:
        print("当前没有房源可导出。")
        return

    keys = listings[0].keys()

    try:
        with open(filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(listings)

        print(f"已导出 {len(listings)} 条房源到 {filename}")
    except Exception as e:
        print("导出失败：", e)



def save_houses(houses, filename="houses.json"):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(houses, f, ensure_ascii=False, indent=2)
    print(f"✅ 已保存到 {filename}（共 {len(houses)} 条）")


def load_houses(filename="houses.json"):
    try:
        with open(filename, "r", encoding="utf-8") as f:
            houses = json.load(f)
        print(f"✅ 已加载 {filename}（共 {len(houses)} 条）")
        return houses
    except FileNotFoundError:
        print(f"⚠️ 找不到 {filename}，请先保存一次。")
        return []
    except json.JSONDecodeError:
        print(f"⚠️ {filename} 文件内容损坏/不是合法JSON。")
        return []





# def score_house(h):
#     # 取字段（按你目前：rent/area/bills）
#     r = parse_rent(h.get("rent"))
#     area = str(h.get("area", "")).strip().lower()
#     bills = str(h.get("bills", "")).strip().lower()

#     score = 0

#     # 1) 价格分：越便宜越高（简单分档）
#     if r is None:
#         score += 0
#     elif r <= 800:
#         score += 30
#     elif r <= 1000:
#         score += 25
#     elif r <= 1200:
#         score += 18
#     elif r <= 1500:
#         score += 10
#     else:
#         score += 5

#     # 2) bills分：包bill加分
#     bills_yes = bills in ("y", "yes", "true", "1", "包", "包含")
#     score += 15 if bills_yes else 0

#     # 3) area分：有内容就给基础分（先简单，后面再接偏好权重）
#     score += 5 if area else 0

#     return score



def rank_houses(listings, budget, weights, area_rank_scores):
    if not listings:
        print("当前没有房源可评分排序。")
        return []

    ranked = []
    for h in listings:
        s = score_house(h, budget, weights, area_rank_scores)
        h["_score"] = s 
        ranked.append(h)

    ranked.sort(key=lambda x: x.get("_score", 0), reverse=True)
    return ranked

def set_preferences():
    budget_str = input("请输入预算(纯数字，如1500): ").strip()
    budget = int(budget_str) if budget_str.isdigit() else 1500

    target_postcode = input("请输入目标 postcode（如 MK40 / MK41 / MK42）: ").strip().upper()
    area_pref_raw = input("请输入区域优先级(如 A,B,C 或 ABC，可回车跳过): ").strip().upper()
    area_prefs = [x.strip() for x in area_pref_raw.replace(" ", "").split(",") if x.strip()] if "," in area_pref_raw else list(area_pref_raw)

    mode = input("选择模式(1省钱 2地段优先 3平衡): ").strip()
    if mode not in ("1", "2", "3"):
        mode = "3"

    if mode == "1":
        weights = {"price": 60, "area": 20, "bills": 20}
    elif mode == "2":
        weights = {"price": 30, "area": 50, "bills": 20}
    else:
        weights = {"price": 45, "area": 35, "bills": 20}

    area_rank_scores = build_area_rank_scores(area_prefs, weights["area"])
    return budget, weights, area_rank_scores, target_postcode

def build_area_rank_scores(area_prefs, area_weight):
    scores = {}

    if len(area_prefs) >= 1:
        scores[area_prefs[0]] = int(area_weight * 1.0)
    if len(area_prefs) >= 2:
        scores[area_prefs[1]] = int(area_weight * 0.6)
    if len(area_prefs) >= 3:
        scores[area_prefs[2]] = int(area_weight * 0.3)

    return scores

from area_module import get_area_score

def score_house(house, budget, weights, area_rank_scores):
    rent = house["rent"]
    area = house["area"]
    bills = house["bills"]

    price_score = weights["price"] * (budget - rent)
    pref_area_score = area_rank_scores.get(area, 0)
    bills_score = weights["bills"] if bills else 0
    
    postcode = house.get("postcode", "")
    postcode_area_score = get_area_score(postcode)

    if postcode_area_score is None:
        postcode_area_score = 0

    total_score = price_score + pref_area_score + postcode_area_score + bills_score
    detail = (
        f"价格分={price_score}, 区域偏好分={pref_area_score}, "
        f"postcode地段分={postcode_area_score}, bills分={bills_score}"
    )
    return total_score, detail

def evaluate_house(house, budget, bills_input):
    rent = house["rent"]
    bills = house["bills"]

    reasons = []

    if rent > budget:
        reasons.append("超预算")

    if bills_input.lower() == "y" and bills is not True:
        reasons.append("不包bills")

    return reasons


def process_house(
    house,
    budget,
    bills_input,
    weights,
    area_rank_scores,
    accepted,
    reason_count
):
    rent = house["rent"]
    area = house["area"]
    bills = house["bills"]

    reasons = evaluate_house(house, budget, bills_input)

    if len(reasons) == 0:
        print(f"✅ 房源通过: rent={rent}, area={area}, bills={bills}")

        score, detail = score_house(house, budget, weights, area_rank_scores)
        house["score"] = score
        house["detail"] = detail
        accepted.append(house)
    else:
        print(f"❌ 房源拒绝: rent={rent}, area={area}, bills={bills}, 原因: {', '.join(reasons)}")
        for r in reasons:
            reason_count[r] += 1

def input_house(state):
    """录入一条房源，返回一个 dict：{"rent": int, "area": "A/B/C", "bills": bool}"""
    # 1) rent
    while True:
        rent_str = input("请输入租金 rent（纯数字，如 1500）: ").strip()
        if rent_str.isdigit():
            rent = int(rent_str)
            break
        print("❌ 租金必须是纯数字。")

    # 2) area
    while True:
        area = input("请输入区域 area（可自由输入，例如 Bedford）: ").strip()
        if area:
            break
        print("❌ area 不能为空。")
        
    # 3) bills
    while True:
        bills_str = input("是否包 bills？(y/n): ").strip().lower()
        if bills_str in ["y", "n"]:
            bills = (bills_str == "y")
            break
        print("❌ 只能输入 y 或 n。")
        
    # 4) postcode
    postcode = input("请输入 postcode (如 E1 6AN): ").strip().upper()

    target_postcode = state["settings"].get("target_postcode")

    # 5) commute
    while True:
        commute_str = input("请输入通勤时间 commute(分钟): ").strip()
        if commute_str.isdigit():
            commute = int(commute_str)
            break
        print("❌ 必须输入数字")

    # 6) bedrooms
    while True:
        bed_str = input("卧室数量 bedrooms: ").strip()
        if bed_str.isdigit():
            bedrooms = int(bed_str)
            break
        print("❌ 必须输入数字")

    house = {
        "rent": rent,
        "area": area,
        "bills": bills,
        "postcode": postcode,
        "commute": commute,
        "bedrooms": bedrooms
    }
    distance_to_target = get_final_distance(house, target_postcode)
    house["distance_to_target"] = distance_to_target

    if distance_to_target is None:
        print("⚠️ 无法自动计算距离，已设为 None")
    else:
        print(f"✅ 已自动计算 distance_to_target = {distance_to_target} miles")

    return house

def filter_houses(houses):
    if not houses:
        print("当前没有房源可筛选。")
        return []

    max_rent_raw = input("最高租金(回车跳过): ").strip()
    need_bills = input("必须包bills吗？(y/n/回车跳过): ").strip().lower()
    area_kw = input("area包含关键词(回车跳过): ").strip().lower()

    max_rent = int(max_rent_raw) if max_rent_raw.isdigit() else None

    results = []
    for h in houses:
        r = parse_rent(h.get("rent"))
        if max_rent is not None and (r is None or r > max_rent):
            continue

        if need_bills in ("y", "n"):
            hb = str(h.get("bills", "")).strip().lower()
            bills_yes = hb in ("y", "yes", "true", "1", "包", "包含")
            if need_bills == "y" and not bills_yes:
                continue
            if need_bills == "n" and bills_yes:
                continue

        if area_kw:
            ha = str(h.get("area", "")).strip().lower()
            if area_kw not in ha:
                continue

        results.append(h)

    print(f"筛选后剩余：{len(results)} 条")
    return results

def recommend_top3(current_list):
    if len(current_list) == 0:
        print("📦 当前没有房源，先用 1) 录入房源")
        return

    # 1) budget
    while True:
        budget_str = input("请输入预算 budget（纯数字，如 1500）: ").strip()
        if budget_str.isdigit():
            budget = int(budget_str)
            break
        print("❌ budget 必须是纯数字")

    # 2) area 偏好
    area_pref_raw = input("请输入区域优先级（如 A,B,C 或 ABC）: ").strip().upper()

    # 3) bills 要求
    bills_input = input("是否必须包 bills？(y/n): ").strip().lower()
    if bills_input not in ["y", "n"]:
        bills_input = "n"

    # 4) mode -> weights
    mode = input("选择模式：1=省钱 2=地段优先 3=平衡: ").strip()
    if mode not in ["1", "2", "3"]:
        mode = "3"

    if mode == "1":
        price_weight, area_weight, bills_weight = 3, 100, 100
    elif mode == "2":
        price_weight, area_weight, bills_weight = 1, 500, 100
    else:
        price_weight, area_weight, bills_weight = 1, 300, 200

    weights = {"price": price_weight, "area": area_weight, "bills": bills_weight}

    # area prefs 解析
    area_clean = area_pref_raw.replace(" ", "").upper()
    if "," in area_clean:
        area_prefs = [x for x in area_clean.split(",") if x in "ABC"]
    else:
        area_prefs = [ch for ch in area_clean if ch in "ABC"]

    area_rank_scores = build_area_rank_scores(area_prefs, area_weight)

    accepted = []
    reason_count = {"超预算": 0, "不包bills": 0}

    # 跑每个房源
    for h in current_list:
        process_house(
            h,
            budget,
            bills_input,
            weights,
            area_rank_scores,
            accepted,
            reason_count
        )

    # 输出结果
    if len(accepted) == 0:
        print("\n❌ 没有可接受房源，无法推荐 Top3")
    else:
        accepted.sort(key=lambda h: h["score"], reverse=True)
        print("\n✅ 推荐 Top 3：")
        for h in accepted[:3]:
            print(f"rent={h['rent']}, area={h['area']}, bills={h['bills']}, score={h['score']}")
            print("   ", h["detail"])

    print(f"\n可接受房源数量：{len(accepted)}")
    print("\n拒绝原因统计：")
    for k, v in reason_count.items():
        print(f"{k}: {v}")

def print_menu():
    print("\n====== 租房App V1 ======")
    print("1) 录入房源")
    print("2) 查看房源")
    print("3) 生成推荐(Top3)")
    print("4) 保存数据")
    print("5) 加载数据")
    print("B) 删除房源")
    print("C) 编辑房源")
    print("A) 清空房源")
    print("E) 导出CSV")
    print("S) 统计信息")
    print("F) 运行筛选(增强)")
    print("R) 重置当前列表(全部房源)")
    print("G) 评分排序Top5")
    print("P) 设置偏好(预算/区域/模式)")
    print("K) 合同风险测试(输入文本)")
    print("L) 结构化风险测试(示例listing)")
    print("0) 退出")

def handle_add_listing(state):
    pass

def handle_view_listings(state):
    pass

def handle_rank_top_n(state):
    pass

def handle_preferences(state):
    pass

def main():
    state = init_state()
    
    houses = state["listings"]
    prefs = state["settings"]
    budget = prefs["budget"] if prefs["budget"] is not None else 1500
    weights = state["weights"]

    weights.setdefault("price", 30)
    weights.setdefault("commute", 20)
    weights.setdefault("bills", 10)
    weights.setdefault("area", 20)
    weights.setdefault("bedrooms", 10)

    current_list = houses

    while True:
        print_menu()
        choice = input("请选择：").strip()

        if choice == "1":
            house = input_house(state)
            if house:
                houses.append(house)
                print(f"✅ 已录入: {house}")
            else:
                print("❌ 房源录入失败")
                
        elif choice == "2":
            if len(current_list) == 0:
                print("📭 当前没有房源。先用 1) 录入房源")
            else:
                print("\n📋 当前房源列表：")
                show_listings(current_list)
        elif choice == "3":
            top3 = get_top_n(state, 3)
            target_postcode = state["settings"].get("target_postcode", "N/A")
            print(f"\n🏆 推荐Top3（按评分排序，目标postcode: {target_postcode}）：\n")

            if not top3:
                print("⚠️ 暂无可推荐房源")
            else:
                for i, r in enumerate(top3, 1):
                    h = r.get("house", {})
                    distance_text = h.get("distance_to_target")
                    if distance_text is None:
                        distance_text = "N/A"
                    print(
                        f"{i}. area={h.get('area')} | rent={h.get('rent')} | bills={h.get('bills')} "
                        f"| postcode={h.get('postcode')} | distance={distance_text} miles "
                        f"| commute={h.get('commute')} | bedrooms={h.get('bedrooms')}"
                    )
                    if r.get("area_preference_score") is not None:
                        print(f"   地区偏好分: {r.get('area_preference_score')} - {r.get('area_preference_reason', '')}")
                    if r.get("area_quality_score") is not None:
                        print(f"   区域质量分: {r.get('area_quality_score')}")
                    reasons = explain_score(h, budget)
                    if reasons:
                        print("推荐原因:", ", ".join(reasons))
        elif choice == "4":
            save_state(state)

        elif choice == "5":
            state = load_state(state)
            houses[:] = state["listings"]
            current_list = houses
            print("✅ 已加载完成")

        elif choice.upper() == "B":
            state = delete_listing(state)
            houses = state["listings"]
            current_list = houses

        elif choice.upper() == "C":
            state = edit_listing(state)
            houses = state["listings"]
            current_list = houses
        elif choice.upper() == "A":
            ok = input("确认清空所有房源？(y/n): ").strip().lower()
            if ok == "y":
                state = clear_listings(state)
                houses[:] = state["listings"]     # 关键：让 houses 这个“引用列表”同步为空
                current_list = houses
            else:
                print("已取消。")
        elif choice.upper() == "E":
            state = strip_scores(state)
            houses = state["listings"]
            current_list = houses
            export_to_csv(houses)
        elif choice.upper() == "S":
            show_stats(houses)
        elif choice.upper() == "F":
            filtered = filter_houses(houses)
            current_list = filtered
            show_listings(filtered)
        elif choice.upper() == "R":
            current_list = houses
            print("已重置为全部房源。")
        elif choice.upper() == "G":
            top5 = get_top_n(state, 5)

            if not top5:
                print("⚠️ 暂无评分结果（请先录入房源或加载数据）")
            else:
                print("\n🏆 评分排序 Top5:\n")
                for i, r in enumerate(top5, 1):

                    h = r["house"]
                    distance_text = h.get("distance_to_target")
                    if distance_text is None:
                        distance_text = "N/A"
                    score_text = r.get("final_score", r.get("_score", "N/A"))
                    detail_text = r.get("detail") or r.get("_detail")
                    print(
                        f"{i}. area={h.get('area')} | rent={h.get('rent')} | bills={h.get('bills')} "
                        f"| postcode={h.get('postcode')} | distance={distance_text} miles "
                        f"| commute={h.get('commute')} | bedrooms={h.get('bedrooms')} "
                        f"| score={r.get('final_score', r.get('_score', r.get('score')))}"
                    )
                    print(f"   总分：{score_text}")
                    if detail_text:
                        print(f"   评分明细：{detail_text}")
                    if r.get("area_preference_score") is not None:
                        print(f"   地区偏好分: {r.get('area_preference_score')} - {r.get('area_preference_reason', '')}")
                    if r.get("area_quality_score") is not None:
                        print(f"   区域质量分: {r.get('area_quality_score')}")
                    reasons = explain_score(h, budget)
                    if reasons:
                        print("推荐原因:", ", ".join(reasons))
        elif choice.upper() == "P":
            budget, weights, area_rank_scores, target_postcode = set_preferences()

            state["settings"]["budget"] = budget
            state["settings"]["target_postcode"] = target_postcode
            state["weights"] = weights
            state["area_rank_scores"] = area_rank_scores
            print("✅ 偏好已更新")
            print(f"budget = {state['settings'].get('budget')}")
            print(f"target_postcode = {state['settings'].get('target_postcode')}")

        elif choice.upper() == "K":
            print("\n--- 合同/风险识别（最小可运行版）---")
            text = input("请输入房源描述/合同文本（可直接粘贴，回车结束）:\n").strip()
            result = calculate_contract_risk_score(text)
            print(f"\n风险分（0-10）：{result.get('risk_score')}")
            if result.get("matched_categories"):
                print("命中类别:", ", ".join(result["matched_categories"]))
            if result.get("matched_keywords"):
                print("命中关键词:", ", ".join(result["matched_keywords"]))
            if result.get("risk_reasons"):
                print("原因:")
                for line in result["risk_reasons"]:
                    print(" -", line)

        elif choice.upper() == "L":
            print("\n--- 结构化风险识别（最小可运行版）---")
            print("1) 低风险示例")
            print("2) deposit 风险示例")
            print("3) no viewing + transfer only 高风险示例")
            print("4) no contract + deposit + urgent payment 组合高风险示例")
            sub = input("请选择示例(1-4): ").strip()

            if sub == "1":
                listing = {
                    "rent": 1500,
                    "deposit_amount": 1500,
                    "viewing_available": True,
                    "contract_available": True,
                    "payment_method": "bank transfer",
                    "notes": "Viewing available. Standard tenancy agreement.",
                    "bills": True,
                }
            elif sub == "2":
                listing = {
                    "rent": "1200",
                    "deposit_amount": "2200",
                    "holding_deposit": "holding deposit non-refundable",
                    "notes": "deposit required",
                }
            elif sub == "3":
                listing = {
                    "rent": 1400,
                    "viewing_available": False,
                    "payment_method": "bank transfer only",
                    "description": "No viewing. Urgent payment needed. Bank transfer only. Pay now.",
                }
            else:
                listing = {
                    "rent": 1300,
                    "deposit_amount": 2200,
                    "contract_available": False,
                    "notes": "No contract, verbal only. Cash only. Urgent payment, pay now.",
                }

            result = calculate_structured_risk_score(listing)
            print(f"\nstructured_risk_score（0-10）：{result.get('structured_risk_score')}")
            if result.get("matched_rules"):
                print("matched_rules:", ", ".join(result["matched_rules"]))
            if result.get("risk_reasons"):
                print("risk_reasons:")
                for line in result["risk_reasons"]:
                    print(" -", line)

        elif choice == "0":
            print("已退出。")
            break

if __name__ == "__main__":
    main()            
