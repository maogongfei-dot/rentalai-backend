from modules.actions.action_engine import build_next_actions


def test_build_next_actions_with_explain_and_risks():
    final_result = {
        "explain_result": {
            "recommendation": "建议先处理高风险项，再决定是否继续。",
            "cons": [
                "风险项：Deposit issue（高风险）",
                "风险项：Break clause unclear（中风险）",
            ],
        },
        "risks": [
            {"title": "Deposit issue", "level": "high"},
            {"title": "Break clause unclear", "level": "medium"},
        ],
        "recommendation": "old recommendation",
    }

    actions = build_next_actions(final_result)

    assert isinstance(actions, list)
    assert len(actions) > 0
    assert any("高风险项" in item for item in actions)


def test_build_next_actions_with_only_medium_risks():
    final_result = {
        "risks": [
            {"title": "Late response", "level": "medium"},
            {"title": "Clause wording vague", "level": "medium"},
        ]
    }

    actions = build_next_actions(final_result)

    assert isinstance(actions, list)
    assert len(actions) > 0
    assert any("中风险项" in item for item in actions)


def test_build_next_actions_with_empty_input():
    actions = build_next_actions({})

    assert isinstance(actions, list)
    assert len(actions) > 0
    assert actions[0] == "先补充更多信息，再继续下一步分析。"
