from modules.decision.decision_engine import build_decision_result


def test_build_decision_result_with_multiple_high_risks():
    final_result = {
        "risks": [
            {"title": "Deposit issue", "level": "high"},
            {"title": "Contract breach", "level": "high"},
        ],
        "missing_info_items": [],
        "next_actions": ["立即处理高风险项：Deposit issue"],
    }

    result = build_decision_result(final_result)

    assert isinstance(result, dict)
    assert result["status"] == "not_recommended"
    assert result["label"] == "当前不建议继续"
    assert isinstance(result["reason"], str)
    assert isinstance(result["confidence"], str)
    assert isinstance(result["action_hint"], str)


def test_build_decision_result_with_one_high_risk():
    final_result = {
        "risks": [
            {"title": "Deposit issue", "level": "high"},
            {"title": "Clause unclear", "level": "medium"},
        ],
        "missing_info_items": ["缺少房东回复记录"],
        "explain_result": {
            "recommendation": "建议先处理高风险项，再决定是否继续。"
        },
    }

    result = build_decision_result(final_result)

    assert isinstance(result, dict)
    assert result["status"] == "review_required"
    assert result["label"] == "需要先处理高风险项"
    assert "高风险" in result["reason"]


def test_build_decision_result_with_many_missing_items():
    final_result = {
        "risks": [],
        "missing_info_items": [
            "缺少整体总结信息",
            "缺少风险明细",
            "缺少下一步行动建议",
            "缺少后续追问问题",
        ],
    }

    result = build_decision_result(final_result)

    assert isinstance(result, dict)
    assert result["status"] == "info_needed"
    assert result["label"] == "需要先补充关键信息"
    assert result["confidence"] == "low"


def test_build_decision_result_can_proceed():
    final_result = {
        "risks": [
            {"title": "Minor clause issue", "level": "medium"}
        ],
        "missing_info_items": [],
        "next_actions": ["继续补查中风险项：Minor clause issue"],
    }

    result = build_decision_result(final_result)

    assert isinstance(result, dict)
    assert result["status"] == "can_proceed"
    assert result["label"] == "可以继续推进"
    assert result["confidence"] == "high"
