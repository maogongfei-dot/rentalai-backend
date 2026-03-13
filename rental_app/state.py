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
        state["weights"] = loaded.get("weights", state.get("weights", DEFAULT_WEIGHTS))
        state["last_action"] = loaded.get("last_action", None)

        print(f"✅ 已加载 state（房源 {len(state['listings'])} 条），来自 {filepath}")
    except FileNotFoundError:
        print(f"⚠️ 没找到 {filepath}，已从空 state 开始")
    return state