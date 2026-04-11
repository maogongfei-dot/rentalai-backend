# modules/chat/user_input_parser.py

from typing import Dict
from modules.query_parser import extract_bedrooms

def parse_user_answer(state: Dict, user_answer: str) -> Dict:
    """
    解析用户输入，并尽量补充到 collected_info
    支持一句话里同时提取多个字段
    """

    answer = user_answer.strip()

    # 记录用户回答
    state["conversation_history"].append({
        "role": "user",
        "content": answer
    })

    answer_lower = answer.lower()

    # 1. budget
    amount_value = extract_amount(answer)
    if amount_value is not None:
        if "budget" not in state["collected_info"]:
            state["collected_info"]["budget"] = amount_value   

    # 2. location
    city_keywords = [
        "伦敦", "曼城", "伯明翰", "利兹",
        "london", "manchester", "birmingham", "leeds"
    ]

    area_keywords = [
        "一区", "二区", "三区", "四区", "五区", "六区",
        "zone 1", "zone 2", "zone 3", "zone 4", "zone 5", "zone 6",
        "东伦敦", "西伦敦", "南伦敦", "北伦敦",
        "东区", "西区", "南区", "北区",
        "市中心", "靠近地铁", "靠近火车站", "近地铁", "近车站"
    ]

    lower_answer = answer.lower()

    # 城市关键词
    if any(x in lower_answer for x in city_keywords):
        if "location" not in state["collected_info"]:
            state["collected_info"]["location"] = answer

    # 区域 / zone / 方位表达
    if any(x in answer for x in area_keywords) or any(x in lower_answer for x in area_keywords):
        if "location" not in state["collected_info"]:
            state["collected_info"]["location"] = answer

    # postcode / 混合区域文本（如 M1 4BT）
    if any(ch.isdigit() for ch in answer) and any(ch.isalpha() for ch in answer):
        if "location" not in state["collected_info"]:
            state["collected_info"]["location"] = answer

    # 用户用了“想住… / 在…附近 / 靠近… ”这类表达
    location_hint_words = ["想住", "住在", "附近", "靠近", "near", "around"]
    if any(x in answer for x in location_hint_words) or any(x in lower_answer for x in location_hint_words):
        if "location" not in state["collected_info"]:
            state["collected_info"]["location"] = answer
    # 3. bedrooms（升级版）
    bedrooms_value = extract_bedrooms(answer)

    if bedrooms_value is not None:
        if "bedrooms" not in state["collected_info"]:
            state["collected_info"]["bedrooms"] = bedrooms_value

    # 4. move_in_date
    move_in_keywords = [
        "马上", "尽快", "下周", "下个月", "这个月", "月底", "月初", "本周",
        "入住", "搬", "搬家", "可入住", "可以入住", "两周后", "一周后",
        "下周末", "周末", "明年", "今年"
    ]

    month_markers = [
        "1月", "2月", "3月", "4月", "5月", "6月",
        "7月", "8月", "9月", "10月", "11月", "12月"
    ]

    day_markers = ["号", "日"]

    if any(x in answer for x in move_in_keywords):
        if "move_in_date" not in state["collected_info"]:
            state["collected_info"]["move_in_date"] = answer
    elif any(x in answer for x in month_markers):
        if "move_in_date" not in state["collected_info"]:
            state["collected_info"]["move_in_date"] = answer

    elif any(x in answer for x in day_markers) and any(ch.isdigit() for ch in answer):
        if "move_in_date" not in state["collected_info"]:
            state["collected_info"]["move_in_date"] = answer

    return state


def extract_amount(text: str):
    """
    从文本里提取简单金额
    例：
    £500
    500
    500镑
    """

    cleaned = text.replace("£", "").replace("镑", "").replace(",", "").strip()

    digits = ""
    for ch in cleaned:
        if ch.isdigit():
            digits += ch

    if digits:
        return int(digits)

    return None


if __name__ == "__main__":
    from chat_entry import chat_entry

    state = chat_entry("房东不退押金怎么办")

    test_answers = [
        "是押金问题",
        "有合同",
        "押金500镑"
    ]

    for ans in test_answers:
        state = parse_user_answer(state, ans)

    print(state)