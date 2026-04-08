# modules/chat/question_engine.py

"""
Question Engine

作用：
- 判断用户信息缺失
- 生成下一步问题
"""

from typing import Dict, List


REQUIRED_FIELDS = [
    "issue_type",   # 问题类型
    "has_contract", # 是否有合同
    "amount",       # 涉及金额（押金等）
]


def detect_missing_fields(state: Dict) -> List[str]:
    missing = []

    for field in REQUIRED_FIELDS:
        if field not in state["collected_info"]:
            missing.append(field)

    return missing


def generate_questions(missing_fields: List[str]) -> List[str]:
    questions = []

    for field in missing_fields:
        if field == "issue_type":
            questions.append("你遇到的问题是什么类型？（押金/涨租/赶人/维修等）")

        elif field == "has_contract":
            questions.append("你有签合同吗？（有/没有）")

        elif field == "amount":
            questions.append("涉及金额是多少？（例如押金£500）")

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