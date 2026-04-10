# modules/chat/question_engine.py

"""
Question Engine

作用：
- 判断用户信息缺失
- 生成下一步问题
"""

from typing import Dict, List


REQUIRED_FIELDS = [
    "budget",        # 预算
    "location",      # 区域
    "bedrooms",      # 房间需求
    "move_in_date",  # 入住时间
]


def detect_missing_fields(state: Dict) -> List[str]:
    missing = []

    for field in REQUIRED_FIELDS:
        if field not in state["collected_info"]:
            missing.append(field)

    return missing

def generate_next_question(state: dict) -> str:
    """
    更自然的聊天式提问（Phase 6）
    """

    # 已有信息
    data = state.get("collected_data", {})

    # === 顺序提问 ===

    if "budget" not in data:
        return "你这次大概预算是多少？一个月房租大概能接受到多少？"

    if "location" not in data:
        return "你想住在哪个区域？有大概的城市或者postcode吗？"

    if "bedrooms" not in data:
        return "是准备自己住，还是合租？大概需要几间房？"

    if "commute" not in data:
        return "平时通勤有要求吗？比如到市中心或者公司大概多久能接受？"

    if "furnishing" not in data:
        return "你是希望带家具的，还是空房也可以？"

    if "move_in_date" not in data:
        return "大概什么时候可以入住？有比较急吗？"

    # === 如果都问完 ===
    return None

def generate_questions(missing_fields: List[str]) -> List[str]:
    questions = []

    for field in missing_fields:
        if field == "budget":
            questions.append("你这次预算大概是多少？一个月房租能接受到多少？")

        elif field == "location":
            questions.append("你想住在哪个区域？有城市、区域或者 postcode 吗？")

        elif field == "bedrooms":
            questions.append("你需要几居？是自己住还是合租？")

        elif field == "move_in_date":
            questions.append("你大概什么时候入住？")

    return questions


def update_state_with_questions(state: Dict) -> Dict:
    missing_fields = detect_missing_fields(state)
    questions = generate_questions(missing_fields)

    state["missing_fields"] = missing_fields
    state["questions"] = questions

    if not missing_fields:
        state["status"] = "ready"

    return state


# 测试
if __name__ == "__main__":
    from chat_entry import chat_entry

    state = chat_entry("房东不退押金怎么办")

    state = update_state_with_questions(state)

    print(state)