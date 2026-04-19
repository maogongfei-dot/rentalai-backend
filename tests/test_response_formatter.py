from modules.output.response_formatter import build_final_response_text


def test_build_final_response_text_with_explain_result():
    final_result = {
        "explain_result": {
            "summary": "当前结果整体可继续推进，但有少量问题需要注意。",
            "pros": ["评分较高", "没有高风险项"],
            "cons": ["合同条款有一处表述不清"],
            "recommendation": "建议继续推进，同时补查合同细节。",
        },
        "summary": "old summary",
        "reasons": ["位置不错", "预算匹配"],
        "risks": [{"title": "Clause unclear", "level": "medium", "detail": "one clause is vague"}],
        "recommendation": "old recommendation",
    }

    text = build_final_response_text(final_result)

    assert isinstance(text, str)
    assert "总结：" in text
    assert "优点：" in text
    assert "需要注意：" in text
    assert "建议：" in text
    assert "- 评分较高" in text
    assert "- 没有高风险项" in text
    assert "- 合同条款有一处表述不清" in text
    assert "原始总结：" in text
    assert "原始 reasons：" in text
    assert "原始 risks：" in text
    assert "原始 recommendation：" in text


def test_build_final_response_text_without_explain_result():
    final_result = {
        "summary": "basic summary",
        "reasons": ["交通方便"],
        "risks": ["late landlord response"],
        "recommendation": "be careful",
    }

    text = build_final_response_text(final_result)

    assert isinstance(text, str)
    assert "原始总结：" in text
    assert "basic summary" in text
    assert "原始 reasons：" in text
    assert "- 交通方便" in text
    assert "原始 risks：" in text
    assert "- late landlord response" in text
    assert "原始 recommendation：" in text
    assert "be careful" in text


def test_build_final_response_text_with_empty_input():
    text = build_final_response_text({})

    assert isinstance(text, str)
    assert text == ""


def test_build_final_response_text_with_dict_risks():
    final_result = {
        "risks": [
            {
                "name": "Deposit issue",
                "severity": "high",
                "description": "deposit terms missing",
            }
        ]
    }

    text = build_final_response_text(final_result)

    assert isinstance(text, str)
    assert "原始 risks：" in text
    assert "- Deposit issue (high): deposit terms missing" in text


def test_build_final_response_text_with_partial_explain_result():
    final_result = {
        "explain_result": {
            "summary": "可以继续。",
            "pros": [],
            "cons": [],
            "recommendation": "先小心核查。",
        }
    }

    text = build_final_response_text(final_result)

    assert isinstance(text, str)
    assert "总结：" in text
    assert "可以继续。" in text
    assert "优点：" in text
    assert "需要注意：" in text
    assert "建议：" in text
    assert "先小心核查。" in text
