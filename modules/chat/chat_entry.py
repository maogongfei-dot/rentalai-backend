# modules/chat/chat_entry.py

from typing import Dict


def init_chat_state(user_input: str) -> Dict:
    state = {
        "original_input": user_input,
        "collected_info": {},
        "missing_fields": [],
        "questions": [],
        "conversation_history": [],
        "analysis_result": None,
        "status": "collecting"
    }
    return state


def chat_entry(user_input: str) -> Dict:
    state = init_chat_state(user_input)

    state["conversation_history"].append({
        "role": "user",
        "content": user_input
    })

    return state


if __name__ == "__main__":
    test_input = "房东不退押金怎么办"
    result = chat_entry(test_input)
    print(result)