# modules/chat/user_input_parser.py

from typing import Dict
import re
from modules.query_parser import extract_bedrooms

def extract_location_value(text: str):
    text_strip = text.strip()
    text_lower = text_strip.lower()

    city_map = {
        "london": "London",
        "manchester": "Manchester",
        "birmingham": "Birmingham",
        "leeds": "Leeds",
        "伦敦": "伦敦",
        "曼城": "曼城",
        "伯明翰": "伯明翰",
        "利兹": "利兹",
        "东伦敦": "东伦敦",
        "西伦敦": "西伦敦",
        "南伦敦": "南伦敦",
        "北伦敦": "北伦敦",
        "东区": "东区",
        "西区": "西区",
        "南区": "南区",
        "北区": "北区",
        "市中心": "市中心",
    }

    for key, value in city_map.items():
        if key in text_lower or key in text_strip:
            return value

    zone_match = re.search(r"\bzone\s*[1-6]\b", text_lower)
    if zone_match:
        return zone_match.group(0).strip().title()

    cn_zone_match = re.search(r"[一二三四五六123456]区", text_strip)
    if cn_zone_match:
        return cn_zone_match.group(0).strip()

    postcode_match = re.search(r"\b[a-z]{1,2}\d[a-z\d]?\s*\d[a-z]{2}\b", text_lower)
    if postcode_match:
        return postcode_match.group(0).upper().strip()

    short_code_match = re.search(r"\b[a-z]{1,2}\d[a-z\d]?\b", text_lower)
    if short_code_match:
        return short_code_match.group(0).upper().strip()

    return None

def extract_move_in_value(text: str):
    text_strip = text.strip()
    text_lower = text_strip.lower()

    exact_keywords = [
        "马上", "尽快", "本周", "下周", "下周末", "周末",
        "这个月", "下个月", "月底", "月初",
        "一周后", "两周后", "今年", "明年",
        "asap", "next week", "next month", "this month",
        "end of month", "start of month", "immediately"
    ]

    for kw in exact_keywords:
        if kw in text_lower or kw in text_strip:
            return kw

    month_match = re.search(r"(1[0-2]|[1-9])月", text_strip)
    if month_match:
        return month_match.group(0)

    day_match = re.search(r"(1[0-9]|2[0-9]|3[01]|[1-9])[号日]", text_strip)
    if day_match:
        return day_match.group(0)

    en_date_match = re.search(
        r"\b(january|february|march|april|may|june|july|august|september|october|november|december)\b",
        text_lower
    )

def parse_user_answer(state: Dict, user_answer: str) -> Dict:
    """
    解析用户输入，并尽量补充到 collected_info
    支持一句话里同时提取多个字段
    """

    answer = user_answer.strip()

    # 记录用户回答（避免首句重复记录）
    history = state.get("conversation_history", [])

    if not history or history[-1].get("content") != answer:
        state["conversation_history"].append({
            "role": "user",
            "content": answer
        })
    answer_lower = answer.lower()

    update_keywords = [
        "改", "换", "不要", "算了", "重新", "改成",
        "change", "update", "instead", "actually"
    ]

    is_update = any(k in answer for k in update_keywords) or any(k in answer_lower for k in update_keywords)

    field_update_keywords = {
        "budget": ["预算", "租金", "price", "budget"],
        "location": ["区域", "位置", "location", "london", "manchester", "postcode", "zone"],
        "bedrooms": ["几居", "bed", "bedroom", "studio", "room", "合租", "shared"],
        "move_in_date": ["入住", "搬", "move", "move in", "入住时间", "下周", "下个月", "月底", "月初"]
    }

field_update_keywords = {
    "budget": ["预算", "租金", "价格", "budget", "price", "pcm"],
    "location": ["区域", "地区", "位置", "location", "area", "postcode"],
    "bedrooms": ["几居", "卧室", "bedroom", "bed", "room", "studio", "shared"],
    "move_in_date": ["入住", "搬", "move", "move in", "入住时间", "下周", "下个月", "月初", "月中", "月末"]
}

def is_field_update(field_name: str, answer: str) -> bool:
    answer_lower = answer.lower()
    is_update = any(k in answer_lower for k in ["改", "换", "update", "change"])

    keywords = field_update_keywords.get(field_name, [])
    return is_update and any(k in answer_lower or k in answer for k in keywords)

    # 1. budget
    amount_value = extract_amount(answer)
    if amount_value is not None:
        if is_field_update("budget") or "budget" not in state["collected_info"]:
            state["collected_info"]["budget"] = amount_value

   # 2. location
    location_value = extract_location_value(answer)

    if location_value is not None:
        if is_field_update("location") or "location" not in state["collected_info"]:
            state["collected_info"]["location"] = location_value
    
    # 3. bedrooms（升级版）
    bedrooms_value = extract_bedrooms(answer)

    if bedrooms_value is not None:
        if is_field_update("bedrooms") or "bedrooms" not in state["collected_info"]:
            state["collected_info"]["bedrooms"] = bedrooms_value
    # 4. move_in_date
    move_in_value = extract_move_in_value(answer)

    if move_in_value is not None:
        if is_field_update("move_in_date") or "move_in_date" not in state["collected_info"]:
            state["collected_info"]["move_in_date"] = move_in_value


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