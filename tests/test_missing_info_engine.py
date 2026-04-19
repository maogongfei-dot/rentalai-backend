from modules.missing_info.missing_info_engine import build_missing_info_items


def test_build_missing_info_items_with_complete_result():
    final_result = {
        "summary": "整体可继续推进",
        "risks": [
            {"title": "Clause issue", "level": "medium"}
        ],
        "reasons": ["位置不错"],
        "explain_result": {
            "summary": "当前结果还可以",
            "recommendation": "建议继续核查后推进"
        },
        "next_actions": ["继续补查合同条款"],
        "followup_questions": ["你是否还有更多合同细节？"],
    }

    result = build_missing_info_items(final_result)

    assert isinstance(result, list)
    assert result == []


def test_build_missing_info_items_with_empty_input():
    result = build_missing_info_items({})

    assert isinstance(result, list)
    assert len(result) > 0
    assert "缺少整体总结信息" in result
    assert "缺少风险明细" in result
    assert "缺少下一步行动建议" in result
    assert "缺少后续追问问题" in result


def test_build_missing_info_items_with_high_risk_but_no_actions():
    final_result = {
        "summary": "有问题",
        "risks": [
            {"title": "Deposit issue", "level": "high"}
        ],
        "reasons": ["价格还行"],
        "explain_result": {
            "summary": "存在高风险",
            "recommendation": "建议先处理高风险"
        },
        "next_actions": [],
        "followup_questions": ["是否已有更多证据？"],
    }

    result = build_missing_info_items(final_result)

    assert isinstance(result, list)
    assert "缺少下一步行动建议" in result
    assert "存在高风险项，但缺少对应处理动作" in result
