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
from module2_scoring import WEIGHT_PRESETS

# Explain Engine (Phase1-5, for Top3/Top5 recommendations)
from explain_engine import (
    explain_score as explain_recommendation_score,
    explain_why_not,
    generate_final_verdict,
    generate_overall_summary,
    generate_confidence_level,
)
# Module7 Explain Engine: 统一解释结构
from engines.explain_engine import build_explanation, format_explanation_for_cli, format_explanation_summary_for_cli, attach_explanation_snapshot, format_comparison_for_cli, format_top_house_summary_for_cli, format_final_recommendation_for_cli, build_final_risk_recommendation, format_final_risk_recommendation_for_cli

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
    print("W) 设置权重预设(balanced/price_first/area_first/commute_first)")
    print("P) 设置偏好(预算/区域/模式)")
    print("K) 合同风险测试(输入文本)")
    print("L) 结构化风险测试(示例listing)")
    print("D) Demo dataset")
    print("0) 退出")

def handle_add_listing(state):
    pass

def handle_view_listings(state):
    pass

def handle_rank_top_n(state):
    pass

def handle_preferences(state):
    pass


def _parse_one_weight(raw: str):
    """仅做清洗：strip；空视为未输入返回 None。不做过重校验。"""
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    return s


def prompt_weight_preset(state):
    """B2-B2-B2-B1/B2-B2-A: 权重预设 + 可选手动 override，写回 state['settings']。"""
    options = list(WEIGHT_PRESETS.keys())
    current = (state.get("settings") or {}).get("weight_preset") or "balanced"
    prompt = (
        f"权重预设 [{', '.join(options)}]，回车=balanced\n"
        f"  当前: {current} → "
    )
    raw = input(prompt).strip()
    if not raw:
        chosen = "balanced"
    else:
        chosen = str(raw).strip().lower()
    if chosen not in WEIGHT_PRESETS:
        chosen = "balanced"
        print("  ⚠ 未知预设，已使用 balanced")
    state.setdefault("settings", {})["weight_preset"] = chosen
    print(f"  ✅ 已设置 weight_preset = {chosen}")

    # B2-B2-B2-A: 5 个可选手动 override，回车=保持 preset（不写回，便于 resolve 用 preset）
    for key in ("price_weight", "commute_weight", "bills_weight", "bedrooms_weight", "area_weight"):
        raw_val = input(f"  Enter {key} override (press Enter to keep preset): ").strip()
        parsed = _parse_one_weight(raw_val)
        if parsed is None:
            state["settings"].pop(key, None)
            continue
        try:
            state["settings"][key] = float(parsed)
        except (TypeError, ValueError):
            state["settings"][key] = parsed
    print("  ✅ 权重设置完成（未填项沿用 preset）")
    return state


def _print_compare_block(compare_explain: dict, n_show: int = 4):
    """B2-B2-B2-B2-A: 打印排名对比摘要，n_show 为最多显示几条（Top3 用 2，Top5 用 4）。"""
    comp_list = compare_explain.get("pairwise_comparisons") or []
    if not comp_list:
        return
    print("\n--- 排名对比 ---")
    for c in comp_list[:n_show]:
        print(f"  {c.get('better_house_label', '')} vs {c.get('lower_house_label', '')}: {c.get('comparison_summary', '')}")
        kd = c.get("key_differences") or []
        if kd:
            print(f"    key differences: {', '.join(kd)}")


def _print_decision_hints(decision_hints: dict, n_show_checklist: int = 5):
    """B2-B2-B2-B2-B1(+A): 打印决策提示与条件化建议、线下核实清单。"""
    if not decision_hints:
        return
    print("\n--- 决策提示 ---")
    primary = decision_hints.get("primary_recommendation")
    if primary:
        print(f"  Primary choice: {primary.get('house_label', '')} — {primary.get('summary', '')}")
        if primary.get("best_if"):
            print(f"  Primary best if: {primary.get('best_if')}")
    backup = decision_hints.get("backup_option")
    if backup:
        print(f"  Backup option: {backup.get('house_label', '')} — {backup.get('summary', '')}")
        if backup.get("best_if"):
            print(f"  Backup best if: {backup.get('best_if')}")
    caution = decision_hints.get("caution_option")
    if caution:
        print(f"  Caution: {caution.get('house_label', '')} — {caution.get('summary', '')}")
        if caution.get("caution_if"):
            print(f"  Caution if: {caution.get('caution_if')}")
    checklist = decision_hints.get("viewing_checklist") or []
    if checklist:
        print("  Viewing checks:")
        for item in checklist[:n_show_checklist]:
            label = item.get("house_label", "")
            checks = item.get("checks") or []
            for c in checks:
                print(f"    - {label}: {c}")
    switch_hints = decision_hints.get("preference_switch_hints") or []
    if switch_hints:
        h = switch_hints[0]
        print("  Preference switch hint:")
        print(f"    {h.get('summary', '')}")
    sim_list = decision_hints.get("preference_simulation") or []
    if sim_list:
        print("  Preference simulation:")
        for s in sim_list[:3]:
            factor = s.get("simulated_factor", "")
            disp = {"price": "price/affordability", "commute": "commute", "bills": "bills", "bedrooms": "bedrooms", "area": "area"}.get(factor, factor)
            print(f"    If {disp} matters more: {s.get('summary', '')}")
    multi_sim = decision_hints.get("multi_factor_simulation") or []
    if multi_sim:
        _disp = {"price": "price/affordability", "commute": "commute", "bills": "bills", "bedrooms": "bedrooms", "area": "area"}
        print("  Multi-factor simulation:")
        for m in multi_sim[:3]:
            factors = m.get("simulated_factors") or []
            if len(factors) >= 2:
                a, b = _disp.get(factors[0], factors[0]), _disp.get(factors[1], factors[1])
                print(f"    If {a} and {b} matter more: {m.get('summary', '')}")
            else:
                print(f"    {m.get('summary', '')}")

    ap = decision_hints.get("action_plan") or {}
    if ap:
        print("  --- Action Plan ---")
        for key, label in [("contact_first", "Contact first"), ("view_first", "View first"), ("keep_as_backup", "Keep as backup"), ("investigate_before_committing", "Investigate before committing")]:
            node = ap.get(key)
            if node:
                print(f"  {label}: {node.get('house_label', '')} — {node.get('summary', '')}")


# ---------- C2-A: 模块化 CLI 输出（统一顺序、标题、长度控制） ----------
# ---------- A2-A: 显示层对齐 ranking_result，轻量辅助读取 ----------

def _get_house_area_score(item):
    """从单条房源项读取 area_score，优先标准字段 scores.area_score，否则 fallback 旧字段。"""
    if not item:
        return None
    scores = item.get("scores") if isinstance(item.get("scores"), dict) else None
    if scores is not None and "area_score" in scores:
        return scores.get("area_score")
    return item.get("area_score")


def _get_house_area_reason(item):
    """从单条房源项读取 area_score_reason，优先标准字段 reasons.area_score_reason。"""
    if not item:
        return ""
    reasons = item.get("reasons") if isinstance(item.get("reasons"), dict) else None
    if reasons is not None:
        v = reasons.get("area_score_reason")
        if v is not None:
            return str(v)
    return str(item.get("area_score_reason") or "")


def _get_house_summary(item):
    """从单条房源项读取 recommendation_summary，优先标准字段 explain.recommendation_summary。"""
    if not item:
        return ""
    ex = item.get("explain") if isinstance(item.get("explain"), dict) else None
    if ex is not None:
        v = ex.get("recommendation_summary")
        if v is not None:
            return str(v)
    ex = item.get("explain") or {}
    return str(ex.get("recommendation_summary") or "")


def print_recommendation_overview(first_result):
    """1. Recommendation Overview: weight_preset, validated_weights, weight_warnings.
    支持从 ranking_result 拼出的 first_result（weight_preset/user_preferences + weights）。"""
    if not first_result:
        return
    preset = first_result.get("weight_preset")
    vw = first_result.get("validated_weights") or {}
    ww = first_result.get("weight_warnings") or []
    print("=== Recommendation Overview ===")
    print(f"  weight_preset: {preset or 'balanced'}")
    if vw:
        parts = [f"{k}={vw.get(k, 1)}" for k in ("price", "commute", "bills", "bedrooms", "area")]
        print(f"  validated_weights: {', '.join(parts)}")
    if ww:
        print("  weight_warnings: " + "; ".join(ww[:3]) + (" ..." if len(ww) > 3 else ""))
    print()


def print_top_recommendations(houses_list, n_show=3):
    """2. Top Recommendations. 优先从标准字段读取：rank, house_label, final_score, scores.area_score, reasons.area_score_reason, explain.recommendation_summary；缺时 fallback 旧字段。Module7: 附带 explanation 摘要。"""
    if not houses_list:
        return
    print("=== Top Recommendations ===")
    for i, r in enumerate(houses_list[:n_show], 1):
        label = r.get("house_label") or f"Rank {i}"
        score = r.get("final_score") or r.get("_score") or r.get("score")
        area_s = _get_house_area_score(r)
        area_reason = _get_house_area_reason(r)
        summary = _get_house_summary(r)
        h = r.get("house") or {}
        print(f"  {label}: {h.get('area', '')} | {h.get('postcode', '')} | rent={h.get('rent')}")
        print(f"    final_score: {score}")
        if area_s is not None:
            print(f"    area_score: {area_s} ({area_reason})")
        if summary:
            print(f"    recommendation_summary: {summary}")
        # Phase3-A3: 若有 ranking_explanation 则简短展示
        if r.get("ranking_explanation"):
            print(f"    ranking_note: {r['ranking_explanation']}")
        # Module7: Explanation Summary（优先用 explanation_summary，Phase3-A1）
        summary = r.get("explanation_summary")
        expl = r.get("explanation")
        if summary:
            txt = format_explanation_summary_for_cli(summary, max_items=2)
        elif expl:
            txt = format_explanation_for_cli(expl)
        else:
            txt = ""
        if txt:
            print("  --- Explanation Summary ---")
            print(txt)
    print()


def print_comparison_insights(compare_explain, n_show=2):
    """3. Comparison Insights: Rank1 vs Rank2, Rank2 vs Rank3 (max n_show)."""
    comp_list = compare_explain.get("pairwise_comparisons") or [] if compare_explain else []
    if not comp_list:
        return
    print("=== Comparison Insights ===")
    for c in comp_list[:n_show]:
        print(f"  {c.get('better_house_label', '')} vs {c.get('lower_house_label', '')}: {c.get('comparison_summary', '')}")
        kd = c.get("key_differences") or []
        if kd:
            print(f"    key_differences: {', '.join(kd)}")
    print()


def print_decision_hints_block(decision_hints):
    """4. Decision Hints: Primary, Backup, Caution only."""
    if not decision_hints:
        return
    primary = decision_hints.get("primary_recommendation")
    backup = decision_hints.get("backup_option")
    caution = decision_hints.get("caution_option")
    if not primary and not backup and not caution:
        return
    print("=== Decision Hints ===")
    if primary:
        print(f"  Primary: {primary.get('house_label', '')} — {primary.get('summary', '')}")
    if backup:
        print(f"  Backup: {backup.get('house_label', '')} — {backup.get('summary', '')}")
    if caution:
        print(f"  Caution: {caution.get('house_label', '')} — {caution.get('summary', '')}")
    print()


def print_preference_switch_hint(decision_hints):
    """5. Preference Switch Hint: at most 1."""
    switch_hints = (decision_hints or {}).get("preference_switch_hints") or []
    if not switch_hints:
        return
    print("=== Preference Switch Hint ===")
    print(f"  {switch_hints[0].get('summary', '')}")
    print()


def print_preference_simulations(decision_hints, n_single=2, n_multi=2):
    """6. Preference Simulations: single-dim n_single, multi-dim n_multi."""
    if not decision_hints:
        return
    sim_list = decision_hints.get("preference_simulation") or []
    multi_sim = decision_hints.get("multi_factor_simulation") or []
    if not sim_list and not multi_sim:
        return
    _disp = {"price": "price/affordability", "commute": "commute", "bills": "bills", "bedrooms": "bedrooms", "area": "area"}
    print("=== Preference Simulations ===")
    for s in sim_list[:n_single]:
        factor = s.get("simulated_factor", "")
        disp = _disp.get(factor, factor)
        print(f"  If {disp} matters more: {s.get('summary', '')}")
    for m in multi_sim[:n_multi]:
        factors = m.get("simulated_factors") or []
        if len(factors) >= 2:
            a, b = _disp.get(factors[0], factors[0]), _disp.get(factors[1], factors[1])
            print(f"  If {a} and {b} matter more: {m.get('summary', '')}")
        else:
            print(f"  {m.get('summary', '')}")
    print()


def print_viewing_checklist(decision_hints, per_house_max=2):
    """7. Viewing Checklist: up to per_house_max checks per house."""
    checklist = (decision_hints or {}).get("viewing_checklist") or []
    if not checklist:
        return
    print("=== Viewing Checklist ===")
    for item in checklist:
        label = item.get("house_label", "")
        checks = (item.get("checks") or [])[:per_house_max]
        for c in checks:
            print(f"  {label}: {c}")
    print()


def print_action_plan(decision_hints):
    """8. Action Plan: contact_first, view_first, keep_as_backup, investigate_before_committing."""
    ap = (decision_hints or {}).get("action_plan") or {}
    if not ap:
        return
    print("=== Action Plan ===")
    for key, label in [("contact_first", "Contact first"), ("view_first", "View first"), ("keep_as_backup", "Keep as backup"), ("investigate_before_committing", "Investigate before committing")]:
        node = ap.get(key)
        if node:
            print(f"  {label}: {node.get('house_label', '')} — {node.get('summary', '')}")
    print()


def print_ranking_report(state, n_show_top=3):
    """Unified CLI output in fixed order: 1–8. 全部优先从标准 ranking_result 读取（A2-A 收口）；无 rr 时从 state 散字段 fallback。缺数据区块自动跳过。"""
    rr = state.get("ranking_result")
    ranked_results = state.get("ranked_results") or []

    if rr:
        # 仅从 ranking_result 顶层字段读取
        metadata = rr.get("metadata") or {}
        weights_block = rr.get("weights") or {}
        user_prefs = rr.get("user_preferences") or {}
        houses = rr.get("houses") or []
        compare_explain = rr.get("compare_explain") or {}
        decision_hints = rr.get("decision_hints") or {}
        preference_switch_hints = rr.get("preference_switch_hints") or []
        preference_simulation = rr.get("preference_simulation") or []
        multi_factor_simulation = rr.get("multi_factor_simulation") or []
        viewing_checklist = rr.get("viewing_checklist") or []
        action_plan = rr.get("action_plan") or {}

        if not metadata and not houses and not ranked_results:
            print("⚠️ 暂无可推荐房源")
            return
        first_result = {
            "weight_preset": user_prefs.get("weight_preset"),
            "validated_weights": weights_block.get("validated_weights"),
            "weight_warnings": weights_block.get("weight_warnings"),
        }
        print_recommendation_overview(first_result)
        print_top_recommendations(houses, n_show=n_show_top)
        if compare_explain and (compare_explain.get("pairwise_comparisons") or []):
            print_comparison_insights(compare_explain, n_show=2)
        # Phase3-A2: 简短展示 comparison_explanation（Top2 对比）
        comp_expl = rr.get("comparison_explanation") or {}
        if comp_expl and comp_expl.get("summary"):
            txt = format_comparison_for_cli(comp_expl, max_items=2)
            if txt:
                print("=== Top 2 Comparison (Phase3-A2) ===")
                print(txt)
                print()
        # Phase3-A3: TopN 推荐理由汇总
        top_sum = rr.get("top_house_summary") or {}
        if top_sum and top_sum.get("summary"):
            txt = format_top_house_summary_for_cli(top_sum, max_items=2)
            if txt:
                print("=== TopN Ranking Summary (Phase3-A3) ===")
                print(txt)
                print()
        # Phase3-A4: 最终推荐结论
        final_rec = rr.get("final_recommendation") or {}
        if final_rec and final_rec.get("final_summary"):
            txt = format_final_recommendation_for_cli(final_rec, max_items=2)
            if txt:
                print("=== Final Recommendation (Phase3-A4) ===")
                print(txt)
                print()
        if decision_hints and (decision_hints.get("primary_recommendation") or decision_hints.get("backup_option") or decision_hints.get("caution_option")):
            print_decision_hints_block(decision_hints)
        if preference_switch_hints:
            print_preference_switch_hint({"preference_switch_hints": preference_switch_hints})
        if preference_simulation or multi_factor_simulation:
            print_preference_simulations({"preference_simulation": preference_simulation, "multi_factor_simulation": multi_factor_simulation}, n_single=2, n_multi=2)
        if viewing_checklist:
            print_viewing_checklist({"viewing_checklist": viewing_checklist}, per_house_max=2)
        if action_plan:
            print_action_plan({"action_plan": action_plan})
    else:
        if not ranked_results:
            print("⚠️ 暂无可推荐房源")
            return
        first_result = {
            "weight_preset": (ranked_results[0] or {}).get("weight_preset"),
            "validated_weights": (ranked_results[0] or {}).get("validated_weights"),
            "weight_warnings": (ranked_results[0] or {}).get("weight_warnings"),
        }
        print_recommendation_overview(first_result)
        print_top_recommendations(ranked_results, n_show=n_show_top)
        compare_explain = state.get("ranked_compare_explain") or {}
        if compare_explain and (compare_explain.get("pairwise_comparisons") or []):
            print_comparison_insights(compare_explain, n_show=2)
        hints = state.get("ranked_decision_hints") or {}
        if hints:
            print_decision_hints_block(hints)
        print_preference_switch_hint(hints)
        print_preference_simulations(hints, n_single=2, n_multi=2)
        print_viewing_checklist(hints, per_house_max=2)
        print_action_plan(hints)


def print_scoring_summary(first_result):
    """在 TopN 结果前打印一轮总览：preset、resolved、validated、override 来源、warnings。"""
    if not first_result:
        return
    preset = first_result.get("weight_preset")
    rw = first_result.get("resolved_weights") or {}
    vw = first_result.get("validated_weights") or {}
    overrides = first_result.get("override_keys") or []
    ww = first_result.get("weight_warnings") or []
    print("--- 本轮评分总览 ---")
    print(f"  preset: {preset or 'balanced'}")
    if rw:
        parts = [f"{k}={rw.get(k, 1)}" for k in ("price", "commute", "bills", "bedrooms", "area")]
        print(f"  resolved_weights: {', '.join(parts)}")
    if vw:
        parts = [f"{k}={vw.get(k, 1)}" for k in ("price", "commute", "bills", "bedrooms", "area")]
        print(f"  validated_weights: {', '.join(parts)}")
    if overrides:
        print(f"  overrides (manual): {', '.join(overrides)}")
    if ww:
        print("  warnings: " + "; ".join(ww[:3]) + (" ..." if len(ww) > 3 else ""))
    print("------------------------")

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
            print_ranking_report(state, n_show_top=3)
            if top3:
                print("=============== AI Summary ===============")
                summary = generate_overall_summary(top3, state.get("settings"))
                for s in summary:
                    print("•", s)
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
        elif choice.upper() == "W":
            state = prompt_weight_preset(state)
        elif choice.upper() == "G":
            top5 = get_top_n(state, 5)
            if not top5:
                print("⚠️ 暂无评分结果（请先录入房源或加载数据）")
            else:
                print("\n🏆 评分排序 Top5:\n")
                print_ranking_report(state, n_show_top=3)
        elif choice.upper() == "D":
            # Demo dataset: 3 sample listings to showcase full AI flow
            demo_list = [
                {
                    "rent": 900,
                    "area": "bedford",
                    "bills": False,
                    "postcode": "MK41",
                    "commute": 20,
                    "bedrooms": 1,
                },
                {
                    "rent": 1200,
                    "area": "bedford",
                    "bills": True,
                    "postcode": "MK40",
                    "commute": 30,
                    "bedrooms": 1,
                },
                {
                    "rent": 1400,
                    "area": "milton keynes",
                    "bills": True,
                    "postcode": "MK9",
                    "commute": 40,
                    "bedrooms": 2,
                },
            ]

            if houses:
                print(f"\n📦 当前已有 {len(houses)} 条房源，将在此基础上追加 Demo 样例。")
            houses.extend(demo_list)
            state["listings"] = houses
            current_list = houses

            print("\n✅ Demo dataset loaded（已追加 3 条示例房源）。")
            print("👉 正在自动生成 Top3 推荐...\n")

            top3 = get_top_n(state, 3)
            target_postcode = state["settings"].get("target_postcode", "N/A")
            print(f"\n🏆 Demo Top3（按评分排序，目标postcode: {target_postcode}）：\n")
            print_ranking_report(state, n_show_top=3)
            if top3:
                print("=============== AI Summary ===============")
                summary = generate_overall_summary(top3, state.get("settings"))
                for s in summary:
                    print("•", s)
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
            # Module7: 追加 explanation
            try:
                result["explanation"] = build_explanation(result, "risk")
            except Exception:
                result["explanation"] = {
                    "summary": "Explanation generation failed.",
                    "recommended": None,
                    "positive_reasons": [],
                    "not_recommended_reasons": [],
                    "neutral_notes": [],
                    "next_actions": [],
                }
            attach_explanation_snapshot(result)
            # Phase4-A1: 最终风险处理结论
            try:
                final_risk = build_final_risk_recommendation(result, label="Current Case")
                result["final_risk_recommendation"] = final_risk
            except Exception:
                result["final_risk_recommendation"] = {}
            print(f"\n风险分（0-10）：{result.get('risk_score')}")
            if result.get("matched_categories"):
                print("命中类别:", ", ".join(result["matched_categories"]))
            if result.get("matched_keywords"):
                print("命中关键词:", ", ".join(result["matched_keywords"]))
            if result.get("risk_reasons"):
                print("原因:")
                for line in result["risk_reasons"]:
                    print(" -", line)
            # Module7: Risk Explanation Summary（优先用 explanation_summary，Phase3-A1）
            summary = result.get("explanation_summary")
            expl = result.get("explanation")
            if summary:
                txt = format_explanation_summary_for_cli(summary, max_items=2)
            elif expl:
                txt = format_explanation_for_cli(expl)
            else:
                txt = ""
            if txt:
                print("\n--- Risk Explanation Summary ---")
                print(txt)
            # Phase4-A1: Final Risk Recommendation
            fr = result.get("final_risk_recommendation") or {}
            if fr and fr.get("final_summary"):
                print("\n--- Final Risk Recommendation (Phase4-A1) ---")
                print(format_final_risk_recommendation_for_cli(fr))

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
            # Module7: 追加 explanation
            try:
                result["explanation"] = build_explanation(result, "risk")
            except Exception:
                result["explanation"] = {
                    "summary": "Explanation generation failed.",
                    "recommended": None,
                    "positive_reasons": [],
                    "not_recommended_reasons": [],
                    "neutral_notes": [],
                    "next_actions": [],
                }
            attach_explanation_snapshot(result)
            # Phase4-A1: 最终风险处理结论
            try:
                final_risk = build_final_risk_recommendation(result, label="Current Case")
                result["final_risk_recommendation"] = final_risk
            except Exception:
                result["final_risk_recommendation"] = {}
            print(f"\nstructured_risk_score（0-10）：{result.get('structured_risk_score')}")
            if result.get("matched_rules"):
                print("matched_rules:", ", ".join(result["matched_rules"]))
            if result.get("risk_reasons"):
                print("risk_reasons:")
                for line in result["risk_reasons"]:
                    print(" -", line)
            # Module7: Risk Explanation Summary（优先用 explanation_summary，Phase3-A1）
            summary = result.get("explanation_summary")
            expl = result.get("explanation")
            if summary:
                txt = format_explanation_summary_for_cli(summary, max_items=2)
            elif expl:
                txt = format_explanation_for_cli(expl)
            else:
                txt = ""
            if txt:
                print("\n--- Risk Explanation Summary ---")
                print(txt)
            # Phase4-A1: Final Risk Recommendation
            fr = result.get("final_risk_recommendation") or {}
            if fr and fr.get("final_summary"):
                print("\n--- Final Risk Recommendation (Phase4-A1) ---")
                print(format_final_risk_recommendation_for_cli(fr))

        elif choice == "0":
            print("已退出。")
            break

if __name__ == "__main__":
    main()            
