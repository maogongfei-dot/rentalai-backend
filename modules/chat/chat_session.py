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


def build_analysis_input_text(state: dict) -> str:
    collected_info = state.get("collected_info", {})
    original_input = state.get("original_input", "")

    budget = collected_info.get("budget", "unknown")
    location = collected_info.get("location", "unknown")
    bedrooms = collected_info.get("bedrooms", "unknown")
    move_in_date = collected_info.get("move_in_date", "unknown")

    lines = [
        f"Budget: £{budget}" if isinstance(budget, int) else f"Budget: {budget}",
        f"Location: {location}",
        f"Bedrooms: {bedrooms}",
        f"Move-in date: {move_in_date}",
        f"User request: {original_input}",
    ]

    return "\n".join(lines)

def build_ai_reply(state: dict) -> str:
    collected_info = state.get("collected_info", {})

    budget = collected_info.get("budget")
    location = collected_info.get("location")
    bedrooms = collected_info.get("bedrooms")
    move_in_date = collected_info.get("move_in_date")

    lines = []
    lines.append("AI总结：")
    lines.append("")
    lines.append("我先帮你把目前的租房需求整理一下：")
    lines.append("")

    if budget is not None:
        lines.append(f"- 预算：£{budget}" if isinstance(budget, int) else f"- 预算：{budget}")

    if location:
        lines.append(f"- 区域：{location}")

    if bedrooms:
        lines.append(f"- 房型：{bedrooms}")

    if move_in_date:
        lines.append(f"- 入住时间：{move_in_date}")

    if len(lines) <= 3:
        lines.append("- 目前还没有收集到有效租房信息")

    lines.append("")
    lines.append("你可以继续直接补充预算、区域、房型或入住时间，我会继续帮你更新。")

    return "\n".join(lines)

def rerun_analysis_with_extra_info(state: dict, extra_info: str) -> dict:
    if not extra_info.strip():
        return state

    original_input = state.get("original_input", "").strip()
    combined_input = f"{original_input}\n补充信息：{extra_info.strip()}"
    state["original_input"] = combined_input

    state = parse_user_answer(state, extra_info)
    state = update_state_with_questions(state)

    if state["status"] == "ready":
        state["status"] = "done"

    return state

def run_followup_prompt() -> str:
    print("")
    followup = input("是否继续补充更多信息？（有/没有）：").strip()

    if followup in ["有", "是", "要", "继续"]:
        extra_info = input("请输入你要补充的信息：").strip()
        return extra_info

    if followup in ["没有", "没", "不用", "不需要"]:
        return ""

    return followup

def run_chat_session():
    state = None

    print("=== RentalAI Chat Session Test ===")

    user_first_input = input("用户输入：").strip()
    state = chat_entry(user_first_input)
    state = parse_user_answer(state, user_first_input)
    state = update_state_with_questions(state)

    while state["status"] != "ready":
        # 每轮先给用户一个当前总结（如果已有信息）
        if state.get("collected_info"):
            summary = build_ai_reply(state)
            print("\n" + summary)
            state["conversation_history"].append({
                "role": "assistant",
                "content": summary
            })
        if not state["questions"]:
            break

        questions = state.get("questions", [])

        if questions:
            if len(state.get("conversation_history", [])) <= 1:
                user_text = state.get("original_input", "").strip()

                if "租房" in user_text:
                    print("AI：好的，我先了解一下你的需求 👍")
                else:
                    print("AI：好的，我先问你几个关键问题")

            # 一次问最多2个问题
            combined_questions = " ".join(questions[:2])

            # 避免重复问同一句问题
            last_ai_msg = ""
            history = state.get("conversation_history", [])
            if history:
                last_ai_msg = history[-1].get("content", "")

            if combined_questions == last_ai_msg:
                state["questions"] = []
                continue
            import random

            prefix_list = [
                "我再确认一下：",
                "我补充问一下：",
                "我帮你确认一个点：",
                "再问你一个关键点：",
                "我继续帮你确认："
            ]

            prefix = random.choice(prefix_list)
            final_question = f"{prefix} {combined_questions}"

            print(f"AI：{final_question}")

            state["conversation_history"].append({
                "role": "assistant",
                "content": final_question
            })

        user_answer = input("你的回答：").strip()

        # 记录当前轮次
        round_count = state.setdefault("round_count", 0)
        state["round_count"] = round_count + 1

        # 超过最大轮数直接结束
        if state["round_count"] >= 6:
            state["status"] = "ready"
        state = parse_user_answer(state, user_answer)
        state = update_state_with_questions(state)

    if state["status"] == "ready":
        # 如果信息不完整，提示用户
        missing = state.get("missing_fields", [])

        if missing:
            print("\nAI：信息还不完整，但我先帮你总结当前情况👇")

        state["analysis_input_text"] = build_analysis_input_text(state)
        state["analysis_result"] = {"ok": True, "data": {}}
        state["status"] = "done"
        
    final_reply = build_ai_reply(state)
    print("\n" + final_reply)
    state["conversation_history"].append({
        "role": "assistant",
        "content": final_reply
    })

    extra_info = run_followup_prompt()

    if extra_info:
        state = rerun_analysis_with_extra_info(state, extra_info)
        print("")
        print("=== 补充信息后的重新分析结果 ===")
        rerun_reply = build_ai_reply(state)
        print(rerun_reply)
        state["conversation_history"].append({
            "role": "assistant",
            "content": rerun_reply
        })
        
if __name__ == "__main__":
    run_chat_session()