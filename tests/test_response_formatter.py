from modules.output.response_formatter import build_final_response_text


def test_build_final_response_text_with_full_sections():
    final_result = {
        "decision_result": {
            "label": "可继续",
            "reason": "关键指标满足阈值",
            "confidence": "high",
            "action_hint": "进入下一阶段验证",
        },
        "explain_result": {
            "summary": "当前结果整体可继续推进，但有少量问题需要注意。",
            "pros": ["评分较高", "没有高风险项"],
            "cons": ["合同条款有一处表述不清"],
            "recommendation": "建议继续推进，同时补查合同细节。",
        },
        "next_actions": ["补充合同附件", "确认付款节点"],
        "followup_questions": ["房东是否接受补充条款？"],
        "missing_info_items": ["最近一次维保记录"],
        "summary": "old summary",
        "reasons": ["位置不错", "预算匹配"],
        "risks": [{"title": "Clause unclear", "level": "medium", "detail": "one clause is vague"}],
        "recommendation": "old recommendation",
    }

    text = build_final_response_text(final_result)

    assert isinstance(text, str)
    assert text.startswith("最终判断：")
    assert "- 状态：可继续" in text
    assert "总结：" in text
    assert "优点：" in text
    assert "需要注意：" in text
    assert "建议：" in text
    assert "下一步建议：" in text
    assert "你还可以继续确认：" in text
    assert "当前还缺：" in text
    assert "- 评分较高" in text
    assert "- 没有高风险项" in text
    assert "- 合同条款有一处表述不清" in text
    assert "原始总结：" in text
    assert "原始 reasons：" in text
    assert "原始 risks：" in text
    assert "原始 recommendation：" in text


def test_build_final_response_text_with_empty_input():
    text = build_final_response_text({})

    assert isinstance(text, str)
    assert text == ""


def test_build_final_response_text_hides_empty_pros_cons_section():
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
    assert "建议：" in text
    assert "优点：" not in text
    assert "需要注意：" not in text


def test_build_final_response_text_with_decision_only():
    final_result = {
        "decision_result": {
            "label": "暂缓",
            "reason": "信息不完整",
        }
    }

    text = build_final_response_text(final_result)

    assert isinstance(text, str)
    assert "最终判断：" in text
    assert "- 状态：暂缓" in text
    assert "- 原因：信息不完整" in text


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
