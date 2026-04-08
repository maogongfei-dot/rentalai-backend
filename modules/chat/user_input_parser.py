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

    # 1. issue_type
    if "押金" in answer:
        state["collected_info"]["issue_type"] = "deposit"
    elif "涨租" in answer:
        state["collected_info"]["issue_type"] = "rent_increase"
    elif "赶" in answer or "搬走" in answer:
        state["collected_info"]["issue_type"] = "eviction"
    elif "维修" in answer or "坏了" in answer or "修" in answer:
        state["collected_info"]["issue_type"] = "repair"

    # 2. has_contract
    if "有合同" in answer or answer in ["有", "有的"]:
        state["collected_info"]["has_contract"] = "yes"
    elif "没合同" in answer or "没有合同" in answer or answer in ["没有", "没", "无"]:
        state["collected_info"]["has_contract"] = "no"

    # 3. amount
    amount_value = extract_amount(answer)
    if amount_value is not None:
        state["collected_info"]["amount"] = amount_value

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