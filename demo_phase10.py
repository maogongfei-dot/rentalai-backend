from tests.test_phase10_integration import build_pipeline_result


def run_demo() -> None:
    demo_cases = [
        (
            "可以继续推进",
            {
                "summary": "整体条件不错",
                "score": 82,
                "risks": [
                    {"title": "Minor clause issue", "level": "medium", "detail": "one clause needs review"}
                ],
                "reasons": ["位置不错", "预算匹配"],
                "recommendation": "可以继续推进，但建议复核条款。",
            },
        ),
        (
            "高风险不建议继续",
            {
                "summary": "存在明显风险",
                "score": 45,
                "risks": [
                    {"title": "Deposit issue", "level": "high", "detail": "deposit protection missing"},
                    {"title": "Contract breach", "level": "high", "detail": "serious contract issue"},
                ],
                "reasons": ["价格还行"],
                "recommendation": "暂时不要继续。",
            },
        ),
        (
            "信息缺失需要补充",
            {
                "summary": "",
                "score": None,
                "risks": [],
                "reasons": [],
                "recommendation": "",
            },
        ),
    ]

    for index, (case_name, base_result) in enumerate(demo_cases, start=1):
        final_result, final_text = build_pipeline_result(base_result)
        decision_status = str((final_result.get("decision_result") or {}).get("status") or "").strip()

        print(f"===== Case {index}: {case_name} =====")
        print(f"decision_status: {decision_status}")
        print("final_text:")
        print(final_text)
        print()


if __name__ == "__main__":
    run_demo()
