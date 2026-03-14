import json
from module2_scoring import DEFAULT_WEIGHTS

DEFAULT_STATE_FILE = "state.json"

def init_state():
    return {
        "listings": [],
        "settings": {
            "budget": 1500,
            "areas": [],
            "min_bed": None,
            "preferred_areas": [],
            "avoided_areas": [],
            "preferred_postcodes": [],
            # 统一权重 (Module5 B2-B2-A)，缺省 1.0
            "price_weight": 1.0,
            "commute_weight": 1.0,
            "bills_weight": 1.0,
            "bedrooms_weight": 1.0,
            "area_weight": 1.0,
            # B2-B2-B2-A: 权重预设，缺省 balanced
            "weight_preset": "balanced",
        },
        "last_action": None,
        "weights": DEFAULT_WEIGHTS,
        "ranked_results": [],
    }

def save_state(state, filepath=DEFAULT_STATE_FILE):
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    print(f"✅ 已保存 state 到 {filepath}（房源 {len(state.get('listings', []))} 条）")

def load_state(state, filepath=DEFAULT_STATE_FILE):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            loaded = json.load(f)

        # 只更新我们关心的key，避免文件缺字段就崩
        state["listings"] = loaded.get("listings", [])
        state["settings"] = loaded.get("settings", state.get("settings", {}))
        # 确保 Module5 地区偏好字段存在，旧存档无则用默认空列表
        s = state["settings"]
        if not isinstance(s.get("preferred_areas"), list):
            s["preferred_areas"] = []
        if not isinstance(s.get("avoided_areas"), list):
            s["avoided_areas"] = []
        if not isinstance(s.get("preferred_postcodes"), list):
            s["preferred_postcodes"] = []
        # B2-B2-B2-A: weight_preset，缺省 balanced
        wp = s.get("weight_preset")
        if wp is None or (isinstance(wp, str) and not wp.strip()):
            s["weight_preset"] = "balanced"
        else:
            s["weight_preset"] = str(wp).strip().lower()
        # 统一权重 (B2-B2-A)：缺字段用 1.0，非法值回退 1.0
        for key in ("price_weight", "commute_weight", "bills_weight", "bedrooms_weight", "area_weight"):
            v = s.get(key)
            if v is None:
                s[key] = 1.0
            else:
                try:
                    s[key] = float(v)
                except (TypeError, ValueError):
                    s[key] = 1.0
        state["weights"] = loaded.get("weights", state.get("weights", DEFAULT_WEIGHTS))
        state["last_action"] = loaded.get("last_action", None)

        print(f"✅ 已加载 state（房源 {len(state['listings'])} 条），来自 {filepath}")
    except FileNotFoundError:
        print(f"⚠️ 没找到 {filepath}，已从空 state 开始")
    return state