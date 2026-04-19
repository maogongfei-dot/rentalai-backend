from modules.explain.explain_engine import build_explanation_result


def test_build_explanation_result_with_high_score_and_low_risk():
    analysis_result = {
        "score": 85,
        "risks": [
            {"title": "Minor admin issue", "level": "low", "detail": "Small paperwork delay"}
        ],
        "reasons": [
            "位置不错",
            "预算匹配",
        ],
    }

    result = build_explanation_result(analysis_result)

    assert isinstance(result, dict)
    assert "summary" in result
    assert "pros" in result
    assert "cons" in result
    assert "recommendation" in result

    assert isinstance(result["summary"], str)
    assert isinstance(result["pros"], list)
    assert isinstance(result["cons"], list)
    assert isinstance(result["recommendation"], str)

    assert len(result["pros"]) > 0
    assert "可以继续" in result["recommendation"] or "继续推进" in result["recommendation"]


def test_build_explanation_result_with_high_risk():
    analysis_result = {
        "score": 52,
        "risks": [
            {"title": "Legal dispute", "level": "high", "detail": "Active unresolved issue"},
            {"title": "Deposit issue", "level": "medium", "detail": "Terms are unclear"},
        ],
        "reasons": [
            "价格还可以",
        ],
    }

    result = build_explanation_result(analysis_result)

    assert isinstance(result, dict)
    assert len(result["cons"]) > 0
    assert "高风险项" in result["summary"] or "高风险" in result["recommendation"]


def test_build_explanation_result_with_empty_input():
    result = build_explanation_result({})

    assert isinstance(result, dict)
    assert set(result.keys()) == {"summary", "pros", "cons", "recommendation"}
    assert isinstance(result["summary"], str)
    assert isinstance(result["pros"], list)
    assert isinstance(result["cons"], list)
    assert isinstance(result["recommendation"], str)
    assert len(result["cons"]) > 0


def test_build_explanation_result_with_string_risks():
    analysis_result = {
        "score": "70",
        "risks": ["contract clause unclear", "late response from landlord"],
        "reasons": ["交通方便"],
    }

    result = build_explanation_result(analysis_result)

    assert isinstance(result, dict)
    assert len(result["cons"]) > 0
    assert len(result["pros"]) > 0
