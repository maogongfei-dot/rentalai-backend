from modules.followup.followup_engine import build_followup_questions


def test_build_followup_questions_with_high_risk():
    final_result = {
        "risks": [
            {"title": "Deposit issue", "level": "high"},
            {"title": "Break clause unclear", "level": "medium"},
        ],
        "explain_result": {
            "recommendation": "建议先处理高风险项，再决定是否继续。"
        },
        "next_actions": [
            "立即处理高风险项：Deposit issue"
        ],
    }

    questions = build_followup_questions(final_result)

    assert isinstance(questions, list)
    assert len(questions) > 0
    assert any("Deposit issue" in item for item in questions)
    assert any("下一步建议" in item or "处理步骤" in item for item in questions)


def test_build_followup_questions_with_medium_risk_only():
    final_result = {
        "risks": [
            {"title": "Late response", "level": "medium"},
            {"title": "Clause vague", "level": "medium"},
        ]
    }

    questions = build_followup_questions(final_result)

    assert isinstance(questions, list)
    assert len(questions) > 0
    assert any("Late response" in item or "Clause vague" in item for item in questions)


def test_build_followup_questions_with_empty_input():
    questions = build_followup_questions({})

    assert isinstance(questions, list)
    assert len(questions) > 0
    assert questions[0] == "你现在最想优先确认的是预算、风险、合同，还是下一步行动？"
