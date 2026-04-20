from modules.explain.explain_engine import build_explanation_result
from modules.actions.action_engine import build_next_actions
from modules.followup.followup_engine import build_followup_questions
from modules.missing_info.missing_info_engine import build_missing_info_items
from modules.decision.decision_engine import build_decision_result
from modules.output.response_formatter import build_final_response_text


def build_pipeline_result(base_result):
    final_result = dict(base_result)

    explain_result = build_explanation_result(final_result)
    final_result["explain_result"] = explain_result

    next_actions = build_next_actions(final_result)
    final_result["next_actions"] = next_actions

    followup_questions = build_followup_questions(final_result)
    final_result["followup_questions"] = followup_questions

    missing_info_items = build_missing_info_items(final_result)
    final_result["missing_info_items"] = missing_info_items

    decision_result = build_decision_result(final_result)
    final_result["decision_result"] = decision_result

    final_text = build_final_response_text(final_result)

    return final_result, final_text


def test_pipeline_can_proceed_case():
    base_result = {
        "summary": "整体条件不错",
        "score": 82,
        "risks": [
            {"title": "Minor clause issue", "level": "medium", "detail": "one clause needs review"}
        ],
        "reasons": ["位置不错", "预算匹配"],
        "recommendation": "可以继续推进，但建议复核条款。",
    }

    final_result, final_text = build_pipeline_result(base_result)

    assert "explain_result" in final_result
    assert "next_actions" in final_result
    assert "followup_questions" in final_result
    assert "missing_info_items" in final_result
    assert "decision_result" in final_result

    assert isinstance(final_result["explain_result"], dict)
    assert isinstance(final_result["next_actions"], list)
    assert isinstance(final_result["followup_questions"], list)
    assert isinstance(final_result["missing_info_items"], list)
    assert isinstance(final_result["decision_result"], dict)

    assert final_result["decision_result"]["status"] in {
        "can_proceed",
        "review_required",
    }
    assert isinstance(final_text, str)
    assert len(final_text) > 0


def test_pipeline_high_risk_case():
    base_result = {
        "summary": "存在明显风险",
        "score": 45,
        "risks": [
            {"title": "Deposit issue", "level": "high", "detail": "deposit protection missing"},
            {"title": "Contract breach", "level": "high", "detail": "serious contract issue"},
        ],
        "reasons": ["价格还行"],
        "recommendation": "暂时不要继续。",
    }

    final_result, final_text = build_pipeline_result(base_result)

    assert final_result["decision_result"]["status"] == "not_recommended"
    assert isinstance(final_result["next_actions"], list)
    assert len(final_result["next_actions"]) > 0
    assert "最终判断：" in final_text or len(final_text) > 0


def test_pipeline_missing_info_case():
    base_result = {
        "summary": "",
        "score": None,
        "risks": [],
        "reasons": [],
        "recommendation": "",
    }

    final_result, final_text = build_pipeline_result(base_result)

    assert final_result["decision_result"]["status"] in {
        "info_needed",
        "can_proceed",
        "review_required",
    }
    assert isinstance(final_result["missing_info_items"], list)
    assert len(final_result["missing_info_items"]) > 0
    assert isinstance(final_text, str)


def test_pipeline_output_contains_main_sections():
    base_result = {
        "summary": "需要进一步核查",
        "score": 60,
        "risks": [
            {"title": "Clause vague", "level": "medium", "detail": "wording is unclear"}
        ],
        "reasons": ["交通方便"],
        "recommendation": "建议继续核查。",
    }

    final_result, final_text = build_pipeline_result(base_result)

    assert isinstance(final_text, str)
    assert len(final_text) > 0

    possible_titles = [
        "总结：",
        "优点：",
        "需要注意：",
        "建议：",
        "下一步建议：",
        "你还可以继续确认：",
        "当前还缺：",
        "最终判断：",
    ]

    assert any(title in final_text for title in possible_titles)
    assert isinstance(final_result["decision_result"], dict)
