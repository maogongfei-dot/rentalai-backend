# modules/chat/chat_session.py

import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
MODULES_DIR = os.path.dirname(CURRENT_DIR)
PROJECT_ROOT = os.path.dirname(MODULES_DIR)

if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from chat_entry import chat_entry
from question_engine import update_state_with_questions
from user_input_parser import parse_user_answer
from modules.contract.contract_pipeline import analyze_contract_pipeline


def build_ai_reply(state: dict) -> str:
    analysis_result = state.get("analysis_result")

    if not isinstance(analysis_result, dict):
        return "系统暂时无法生成分析结果。"

    if analysis_result.get("ok") is not True:
        error = analysis_result.get("error") or "未知错误"
        return f"分析失败：{error}"

    data = analysis_result.get("data") or {}
    risk = data.get("risk") or {}
    explanations = data.get("explanations") or {}

    issue_type = state.get("collected_info", {}).get("issue_type", "unknown")
    amount = state.get("collected_info", {}).get("amount", "未知")
    has_contract = state.get("collected_info", {}).get("has_contract", "未知")

    risk_level = risk.get("risk_level", "unknown")
    human_explanation = explanations.get("human_explanation") or explanations.get("overall_explanation") or "暂无说明"

    issue_type_map = {
        "deposit": "押金问题",
        "rent_increase": "涨租问题",
        "eviction": "赶人/解约问题",
        "repair": "维修问题",
    }

    risk_level_map = {
        "high": "高风险",
        "medium": "中风险",
        "low": "低风险",
        "unknown": "未知风险",
    }

    has_contract_map = {
        "yes": "有合同",
        "no": "没有合同",
        "未知": "未知",
    }

    lines = []
    lines.append("=== AI 对话分析结果 ===")
    lines.append(f"问题类型：{issue_type_map.get(issue_type, issue_type)}")
    lines.append(f"是否有合同：{has_contract_map.get(has_contract, has_contract)}")
    lines.append(f"涉及金额：£{amount}" if isinstance(amount, int) else f"涉及金额：{amount}")
    lines.append(f"风险等级：{risk_level_map.get(risk_level, risk_level)}")
    lines.append("")
    lines.append("系统解释：")
    lines.append(human_explanation)

    return "\n".join(lines)


def run_chat_session():
    state = None

    print("=== RentalAI Chat Session Test ===")

    user_first_input = input("用户输入：").strip()
    state = chat_entry(user_first_input)
    state = update_state_with_questions(state)

    while state["status"] != "ready":
        if not state["questions"]:
            break

        current_question = state["questions"][0]
        print(f"AI提问：{current_question}")

        user_answer = input("你的回答：").strip()
        state = parse_user_answer(state, user_answer)
        state = update_state_with_questions(state)

    if state["status"] == "ready":
        analysis_result = analyze_contract_pipeline(state["original_input"])
        state["analysis_result"] = analysis_result
        state["status"] = "done"

    print("\n=== 最终收集结果 ===")
    print(state)

    print("\n" + build_ai_reply(state))


if __name__ == "__main__":
    run_chat_session()