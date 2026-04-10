# modules/chat/user_input_parser.py

from typing import Dict


def parse_user_answer(state: Dict, user_answer: str) -> Dict:
    """
    解析用户输入，并尽量补充到 collected_info
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
        state["collected_info"]["budget"] = amount_value

    # 2. location
    if any(x in answer for x in ["伦敦", "曼城", "伯明翰", "利兹", "London", "Manchester", "Birmingham", "Leeds"]):
        state["collected_info"]["location"] = answer

    if any(ch.isdigit() for ch in answer) and any(ch.isalpha() for ch in answer):
        state["collected_info"]["location"] = answer

    # 3. bedrooms
    if "一居" in answer or "1居" in answer or "1 bed" in answer.lower():
        state["collected_info"]["bedrooms"] = "1"
    elif "两居" in answer or "2居" in answer or "2 bed" in answer.lower():
        state["collected_info"]["bedrooms"] = "2"
    elif "三居" in answer or "3居" in answer or "3 bed" in answer.lower():
        state["collected_info"]["bedrooms"] = "3"
    elif "合租" in answer:
        state["collected_info"]["bedrooms"] = "shared"
    elif "自己住" in answer:
        state["collected_info"]["bedrooms"] = "private"

    # 4. move_in_date
    if any(x in answer for x in ["马上", "尽快", "下周", "下个月", "这个月", "月底"]):
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